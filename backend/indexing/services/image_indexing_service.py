import os

from monitoring import logger

from core import embedder_manager
from core.singleton import Singleton
from models.models import SessionLocal
from indexing.consistency.consistency_checker import ConsistencyChecker
from indexing.file_types import scan_image_paths
from indexing.watchers.file_watcher_service import FileWatcherService
from indexing.queue_manager.index_queue_manager import IndexQueueManager
from indexing.repositories.repositories import DirectoryRepository, ImageRepository
from settings import settings


@Singleton
class ImageIndexingService:
    def __init__(self):
        self.index_queue_manager = IndexQueueManager.instance()
        self.file_watcher_service = FileWatcherService.instance()
        self.consistency_checker = ConsistencyChecker(settings.directory.consistency_check_interval)

    @property
    def embedders(self):
        # Resolved dynamically because models are loaded lazily after onboarding.
        return embedder_manager.get_image_embedders()

    def add_directory(self, path: str) -> int:
        logger.info(f"Attempting to add directory: {path}")
        if not os.path.exists(path):
            logger.error(f"Directory not found: {path}")
            raise FileNotFoundError(f"Path {path} does not exist")
        session = SessionLocal()
        try:
            directory_repo = DirectoryRepository(session)
            directory = directory_repo.get_by_path(path)
            if not directory:
                directory = directory_repo.create(path)

            # Find and add images from the filesystem
            image_paths = sorted(scan_image_paths(path))
            image_repo = ImageRepository(session)
            image_repo.add_new_images(directory.id, image_paths)

            # Queue for indexing
            self.index_queue_manager.add_to_queue(directory.id, path, priority=1)
            # Start filesystem indexing for changes
            self.file_watcher_service.add_directory(directory.id, path)
            logger.info(f"Directory {path} (ID: {directory.id}) added successfully")
            return directory.id
        except Exception as e:
            logger.error(f"Error adding directory {path}: {e}", exc_info=True)
            session.rollback()
            raise RuntimeError(f"Error adding directory: {e}")
        finally:
            session.close()

    def remove_directory(self, path: str):
        logger.info(f"Removing directory: {path}")
        # Stop watching first: otherwise events fired while the rows are being
        # deleted would re-add the very images being removed.
        self.file_watcher_service.remove_directory(path)
        session = SessionLocal()
        try:
            directory_repo = DirectoryRepository(session)
            directory = directory_repo.get_by_path(path)
            if directory:
                # Drops the directory's vectors and image rows as well.
                directory_repo.delete(directory)
        except Exception as e:
            logger.error(f"Error removing directory {path}: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def start(self):
        logger.info("Starting ImageIndexingService")
        self.file_watcher_service.start()
        self.consistency_checker.start()
        # Re-queue and re-watch all tracked directories from the database.
        session = SessionLocal()
        try:
            directory_repo = DirectoryRepository(session)
            directories = directory_repo.get_all()
            for directory in directories:
                if os.path.exists(directory.path):
                    self.index_queue_manager.add_to_queue(directory.id, directory.path, priority=1)
                    self.file_watcher_service.add_directory(directory.id, directory.path)
                else:
                    self.remove_directory(directory.path)
        finally:
            session.close()
