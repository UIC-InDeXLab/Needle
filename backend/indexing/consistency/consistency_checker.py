import os
import threading
import time

from sqlalchemy.orm import Session

from core import embedder_manager
from models.models import SessionLocal, Directory, Image
from indexing.repositories.repositories import DirectoryRepository, ImageRepository, MilvusRepository
from monitoring import logger
from settings import settings


class ConsistencyChecker:
    def __init__(self, interval: int = 3600):
        self.interval = interval
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        while True:
            time.sleep(self.interval)
            self.check_consistency()

    def check_consistency(self):
        logger.info("Running system-wide consistency check")
        session = SessionLocal()
        try:
            directory_repo = DirectoryRepository(session)
            directories = directory_repo.get_all()
            for directory in directories:
                self.check_directory(session, directory)
            logger.info("Consistency check completed")
        except Exception as e:
            logger.error(f"Consistency check error: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def check_directory(self, session: Session, directory: Directory):
        logger.info(f"Checking consistency for directory {directory.path} (ID: {directory.id})")
        if not os.path.exists(directory.path):
            logger.warning(f"Directory missing: {directory.path}. Removing from system.")
            DirectoryRepository(session).delete(directory)
            return

        # Gather filesystem image paths
        fs_paths = set()
        for entry in os.scandir(directory.path):
            if entry.is_file() and entry.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                fs_paths.add(entry.path)
            elif entry.is_dir() and settings.directory.recursive_indexing:
                for root, _, files in os.walk(entry.path):
                    for file in files:
                        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                            fs_paths.add(os.path.join(root, file))

        # Get database image paths
        image_repo = ImageRepository(session)
        db_images = session.query(Image).filter(Image.directory_id == directory.id).all()
        db_paths = {img.path for img in db_images}

        new_paths = fs_paths - db_paths
        deleted_paths = db_paths - fs_paths
        logger.info(f"Directory {directory.path}: {len(new_paths)} new images, {len(deleted_paths)} missing images")

        # Add new images to DB
        for path in new_paths:
            if not image_repo.get_by_path(path):
                session.add(Image(path=path, directory_id=directory.id, is_indexed=False))
        session.commit()

        # Remove deleted images from DB and Milvus
        for path in deleted_paths:
            image = image_repo.get_by_path(path)
            if image:
                for embedder_name in embedder_manager.get_image_embedders().keys():
                    MilvusRepository().delete_entries(embedder_name, f"image_path == '{path}'")
                image_repo.delete(image)
        session.commit()
