import logging
import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from PIL import Image as PImage
from pymilvus import Collection
from sqlalchemy.orm import Session
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from core.embedders import EmbedderManager
from core.singleton import Singleton
from database.database_manager import SessionLocal, Directory, Image
from settings import settings

# Configure logging globally
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# ─────────────────────────────────────────────────────────────────────────────
# Repository Classes
# ─────────────────────────────────────────────────────────────────────────────

class DirectoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_path(self, path: str) -> Directory:
        return self.session.query(Directory).filter(Directory.path == path).first()

    def create(self, path: str) -> Directory:
        directory = Directory(path=path, is_indexed=False)
        self.session.add(directory)
        self.session.commit()
        self.session.refresh(directory)
        logger.debug(f"Created directory entry with ID {directory.id} for path {path}")
        return directory

    def get_all(self) -> List[Directory]:
        return self.session.query(Directory).all()

    def delete(self, directory: Directory):
        self.session.delete(directory)
        self.session.commit()


class ImageRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_path(self, path: str) -> Image:
        return self.session.query(Image).filter(Image.path == path).first()

    def add_new_images(self, directory_id: int, image_paths: List[str]) -> List[Image]:
        new_images = []
        for path in image_paths:
            if not self.get_by_path(path):
                image = Image(path=path, directory_id=directory_id, is_indexed=False)
                self.session.add(image)
                new_images.append(image)
        self.session.commit()
        logger.info(f"Added {len(new_images)} new images to database for directory {directory_id}")
        return new_images

    def get_unindexed_images(self, directory_id: int) -> List[Image]:
        return self.session.query(Image).filter(
            Image.directory_id == directory_id,
            Image.is_indexed == False
        ).all()

    def delete(self, image: Image):
        self.session.delete(image)
        self.session.commit()


class MilvusRepository:
    def delete_entries(self, embedder_name: str, expr: str):
        collection = Collection(embedder_name)
        result = collection.delete(expr)
        collection.flush()
        logger.info(f"Deleted {result.delete_count} entries in Milvus collection '{embedder_name}' using expr {expr}")
        return result

    def insert_entries(self, embedder_name: str, entries: List[Dict]):
        collection = Collection(embedder_name)
        collection.insert(entries)
        collection.flush()
        logger.debug(f"Inserted {len(entries)} entries into Milvus collection '{embedder_name}'")

    def query_entries(self, embedder_name: str, expr: str, output_fields: List[str], batch_size: int = 1000):
        collection = Collection(embedder_name)
        return collection.query_iterator(expr=expr, output_fields=output_fields, batch_size=batch_size)


# ─────────────────────────────────────────────────────────────────────────────
# Embedder Service
# ─────────────────────────────────────────────────────────────────────────────

class EmbedderService:
    def __init__(self):
        self.embedders = EmbedderManager.instance().get_image_embedders()

    def compute_embedding(self, image_path: str) -> Dict[str, List[float]]:
        image = PImage.open(image_path).convert("RGB")
        return {name: embedder.embed(image) for name, embedder in self.embedders.items()}

    def compute_batch_embeddings(self, image_paths: List[str], max_workers: int) -> Dict[str, Dict[str, List[float]]]:
        embeddings = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.compute_embedding, path): path for path in image_paths}
            for future in as_completed(futures):
                path = futures[future]
                try:
                    embeddings[path] = future.result()
                    logger.debug(f"Computed embedding for image: {path}")
                except Exception as e:
                    logger.error(f"Error embedding image {path}: {e}", exc_info=True)
        return embeddings


# ─────────────────────────────────────────────────────────────────────────────
# Directory Indexer
# ─────────────────────────────────────────────────────────────────────────────

class DirectoryIndexer:
    def __init__(self, embedder_service: EmbedderService, milvus_repo: MilvusRepository):
        self.embedder_service = embedder_service
        self.milvus_repo = milvus_repo

    def index_directory(self, directory_id: int, directory_path: str, session: Session):
        logger.info(f"Starting indexing for directory {directory_path} (ID: {directory_id})")
        image_repo = ImageRepository(session)
        unindexed_images = image_repo.get_unindexed_images(directory_id)
        total_images = len(unindexed_images)
        if total_images == 0:
            logger.info(f"No images to index in directory {directory_path}")
            return

        batch_size = settings.directory.batch_size
        for i in range(0, total_images, batch_size):
            batch = unindexed_images[i:i+batch_size]
            batch_paths = [img.path for img in batch]
            logger.debug(f"Processing batch {i // batch_size + 1} with {len(batch)} images")
            embeddings = self.embedder_service.compute_batch_embeddings(
                batch_paths, settings.directory.num_embedding_workers
            )

            # For each image, update Milvus and mark as indexed
            for img in batch:
                if img.path in embeddings:
                    for embedder_name, emb in embeddings[img.path].items():
                        self.milvus_repo.insert_entries(embedder_name, [{
                            "directory_id": directory_id,
                            "image_path": img.path,
                            "embedding": emb
                        }])
                    img.is_indexed = True
            session.commit()

        # Mark directory as fully indexed
        directory = session.query(Directory).get(directory_id)
        directory.is_indexed = True
        session.commit()
        logger.info(f"Completed indexing for directory {directory_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Index Queue Manager
# ─────────────────────────────────────────────────────────────────────────────

@Singleton
class IndexQueueManager:
    def __init__(self):
        self.index_queue = queue.PriorityQueue()
        self.processing_paths = set()
        self.queue_lock = threading.Lock()
        self.index_workers = ThreadPoolExecutor(max_workers=settings.directory.num_watcher_workers)
        self.embedder_service = EmbedderService()
        self.milvus_repo = MilvusRepository()
        self.directory_indexer = DirectoryIndexer(self.embedder_service, self.milvus_repo)

    def add_to_queue(self, directory_id: int, path: str, priority: int = 0):
        with self.queue_lock:
            if (directory_id, path) not in self.processing_paths:
                self.index_queue.put((priority, (directory_id, path)))
                self.processing_paths.add((directory_id, path))
                logger.debug(f"Queued directory {path} (ID: {directory_id}) with priority {priority}")
                self.index_workers.submit(self._process_queue)

    def _process_queue(self):
        while not self.index_queue.empty():
            priority, (directory_id, path) = self.index_queue.get()
            session = SessionLocal()
            try:
                self.directory_indexer.index_directory(directory_id, path, session)
            finally:
                session.close()
                with self.queue_lock:
                    self.processing_paths.discard((directory_id, path))
                logger.debug(f"Finished processing directory {path} (ID: {directory_id})")


# ─────────────────────────────────────────────────────────────────────────────
# File Watcher Service and Image Change Handler
# ─────────────────────────────────────────────────────────────────────────────

@Singleton
class FileWatcherService:
    def __init__(self):
        self.observer = Observer()
        self.handlers = {}

    def add_directory(self, directory_id: int, directory_path: str, embedders: Dict):
        handler = ImageChangeHandler(directory_id, directory_path, embedders)
        watch = self.observer.schedule(handler, directory_path, recursive=True)
        self.handlers[directory_path] = (handler, watch)
        logger.info(f"Started filesystem watcher for {directory_path}")

    def remove_directory(self, directory_path: str):
        if directory_path in self.handlers:
            handler, watch = self.handlers[directory_path]
            self.observer.unschedule(watch)
            del self.handlers[directory_path]
            logger.info(f"Stopped filesystem watcher for {directory_path}")

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()


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
                    MilvusRepository().delete_entries(embedder_name, f"directory_id == {self.directory_id} && image_path == '{path}'")
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
                    milvus_repo.delete_entries(embedder_name, f"directory_id == {self.directory_id} and image_path == '{src_path}'")
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


# ─────────────────────────────────────────────────────────────────────────────
# Consistency Checker
# ─────────────────────────────────────────────────────────────────────────────

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
                for embedder_name in EmbedderManager.instance().get_image_embedders().keys():
                    MilvusRepository().delete_entries(embedder_name, f"image_path == '{path}'")
                image_repo.delete(image)
        session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# High-Level Service: ImageIndexingService (Facade)
# ─────────────────────────────────────────────────────────────────────────────

@Singleton
class ImageIndexingService:
    def __init__(self):
        self.index_queue_manager = IndexQueueManager.instance()
        self.file_watcher_service = FileWatcherService.instance()
        self.consistency_checker = ConsistencyChecker(settings.directory.consistency_check_interval)
        self.embedders = EmbedderManager.instance().get_image_embedders()

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
            # Start filesystem monitoring for changes
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
            # Stop filesystem monitoring
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
