from monitoring import logger

from typing import Dict

from watchdog.events import FileSystemEventHandler

from models.models import SessionLocal, Image
from indexing.queue_manager.index_queue_manager import IndexQueueManager
from indexing.repositories.repositories import ImageRepository, MilvusRepository


class ImageChangeHandler(FileSystemEventHandler):
    def __init__(self, directory_id: int, directory_path: str, embedders: Dict):
        self.directory_id = directory_id
        self.directory_path = directory_path
        self.embedders = embedders
        super().__init__()
        logger.debug(f"Created ImageChangeHandler for directory {directory_path} (ID: {directory_id})")

    def _is_image(self, path: str) -> bool:
        return path.lower().endswith(('.png', '.jpg', '.jpeg'))

    def on_created(self, event):
        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"New image detected: {event.src_path}")
            self._handle_new_image(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"Image deleted: {event.src_path}")
            self._handle_deleted_image(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"Image modified: {event.src_path}")
            self._handle_modified_image(event.src_path)

    def on_moved(self, event):
        src_path = event.src_path
        dest_path = event.dest_path
        if not event.is_directory and self._is_image(dest_path):
            logger.info(f"Image moved: {src_path} -> {dest_path}")
            self._handle_moved_image(src_path, dest_path)

    def _handle_new_image(self, path: str):
        session = SessionLocal()
        try:
            image_repo = ImageRepository(session)
            if not image_repo.get_by_path(path):
                session.add(Image(path=path, directory_id=self.directory_id, is_indexed=False))
                session.commit()
                logger.info(f"Added new image to database: {path}")
                # Queue the directory for re-indexing
                IndexQueueManager.instance().add_to_queue(self.directory_id, self.directory_path, priority=0)
        except Exception as e:
            logger.error(f"Error handling new image {path}: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def _handle_deleted_image(self, path: str):
        session = SessionLocal()
        try:
            image_repo = ImageRepository(session)
            image = image_repo.get_by_path(path)
            if image:
                for embedder_name in self.embedders.keys():
                    MilvusRepository().delete_entries(embedder_name, f"image_path == '{path}'")
                image_repo.delete(image)
                logger.info(f"Deleted image from database: {path}")
        except Exception as e:
            logger.error(f"Error handling deleted image {path}: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def _handle_modified_image(self, path: str):
        session = SessionLocal()
        try:
            image_repo = ImageRepository(session)
            image = image_repo.get_by_path(path)
            if image and image.is_indexed:
                logger.info(f"Re-indexing modified image: {path}")
                image.is_indexed = False
                for embedder_name in self.embedders.keys():
                    MilvusRepository().delete_entries(embedder_name,
                                                      f"directory_id == {self.directory_id} && image_path == '{path}'")
                session.commit()
                IndexQueueManager.instance().add_to_queue(self.directory_id, self.directory_path, priority=0)
        except Exception as e:
            logger.error(f"Error handling modified image {path}: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def _handle_moved_image(self, src_path: str, dest_path: str):
        session = SessionLocal()
        try:
            image_repo = ImageRepository(session)
            image = image_repo.get_by_path(src_path)
            if image:
                for embedder_name in self.embedders.keys():
                    milvus_repo = MilvusRepository()
                    # Query current embeddings
                    results = milvus_repo.query_entries(
                        embedder_name,
                        f"directory_id == {self.directory_id} and image_path == '{src_path}'",
                        ["embedding"]
                    )
                    embeddings = []
                    # Collect embeddings from query results
                    for res in results:
                        for item in res:
                            embeddings.append(item["embedding"])
                    milvus_repo.delete_entries(embedder_name,
                                               f"directory_id == {self.directory_id} and image_path == '{src_path}'")
                    for emb in embeddings:
                        milvus_repo.insert_entries(embedder_name, [{
                            "directory_id": self.directory_id,
                            "image_path": dest_path,
                            "embedding": emb
                        }])
                # Update DB record
                image.path = dest_path
                session.commit()
                logger.info(f"Updated image path from {src_path} to {dest_path}")
        except Exception as e:
            logger.error(f"Error handling moved image {src_path} -> {dest_path}: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()
