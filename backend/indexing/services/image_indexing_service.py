import os
from typing import List

from monitoring import logger

from core import embedder_manager
from core.singleton import Singleton
from models.models import SessionLocal, Image
from indexing.consistency.consistency_checker import ConsistencyChecker
from indexing.watchers.file_watcher_service import FileWatcherService
from indexing.queue_manager.index_queue_manager import IndexQueueManager
from indexing.repositories.repositories import DirectoryRepository, ImageRepository, MilvusRepository
from settings import settings


@Singleton
class ImageIndexingService:
    def __init__(self):
        self.index_queue_manager = IndexQueueManager.instance()
        self.file_watcher_service = FileWatcherService.instance()
        self.consistency_checker = ConsistencyChecker(settings.directory.consistency_check_interval)
        self.embedders = embedder_manager.get_image_embedders()

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
            image_paths = self._get_image_paths(path)
            image_repo = ImageRepository(session)
            image_repo.add_new_images(directory.id, image_paths)
            session.commit()

            # Queue for indexing
            self.index_queue_manager.add_to_queue(directory.id, path, priority=1)
            # Start filesystem indexing for changes
            self.file_watcher_service.add_directory(directory.id, path, self.embedders)
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
        session = SessionLocal()
        try:
            directory_repo = DirectoryRepository(session)
            directory = directory_repo.get_by_path(path)
            if directory:
                # Delete Milvus entries for all embedders
                for embedder_name in self.embedders.keys():
                    MilvusRepository().delete_entries(embedder_name, f"directory_id == {directory.id}")
                session.query(Image).filter(Image.directory_id == directory.id).delete()
                directory_repo.delete(directory)
                session.commit()
            # Stop filesystem indexing
            self.file_watcher_service.remove_directory(path)
        except Exception as e:
            logger.error(f"Error removing directory {path}: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def _get_image_paths(self, path: str) -> List[str]:
        image_paths = []
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False) and settings.directory.recursive_indexing:
                image_paths.extend(self._get_image_paths(entry.path))
            elif entry.is_file() and entry.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_paths.append(entry.path)
        return image_paths

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
                    self.file_watcher_service.add_directory(directory.id, directory.path, self.embedders)
                else:
                    self.remove_directory(directory.path)
        finally:
            session.close()
