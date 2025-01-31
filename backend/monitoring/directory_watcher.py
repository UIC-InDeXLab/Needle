import logging
import os
import queue
import threading
import time
from collections import defaultdict
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

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


@Singleton
class ImageIndexer:
    def __init__(self):
        self.observer = Observer()
        self.handlers = {}
        self.embedders = EmbedderManager.instance().get_image_embedders()
        self.consistency_check_interval = 3600
        self.index_queue = queue.PriorityQueue()
        self.processing_paths = set()
        self.queue_lock = threading.Lock()
        self.index_workers = ThreadPoolExecutor(max_workers=settings.directory.num_watcher_workers)
        logger.info("ImageIndexer initialized with indexing queue")

    def add_directory(self, path: str) -> int:
        """
        Add directory to tracking and queue for background indexing
        """

        logger.info(f"Attempting to add directory: {path}")
        if not os.path.exists(path):
            logger.error(f"Directory not found: {path}")
            raise FileNotFoundError(f"Path {path} does not exist")

        session = SessionLocal()
        try:
            # Check if directory already exists
            directory = session.query(Directory).filter(Directory.path == path).first()
            if not directory:
                logger.info(f"Creating new directory entry: {path}")
                directory = Directory(path=path, is_indexed=False)
                session.add(directory)
                session.commit()
                session.refresh(directory)
                logger.debug(f"Created directory ID {directory.id} for path {path}")

            # Find and add all images to database as non-indexed
            image_paths = self._get_image_paths(path)
            logger.info(f"Found {len(image_paths)} images in directory {path}")

            new_images = [
                Image(path=img_path, directory_id=directory.id, is_indexed=False)
                for img_path in image_paths
                if not session.query(Image).filter(Image.path == img_path).first()
            ]
            session.bulk_save_objects(new_images)
            session.commit()
            logger.info(f"Added {len(new_images)} new images to database for directory {path}")


            self._add_to_index_queue(directory.id, path, priority=1)
            logger.debug(f"Added directory {directory.id} to indexing queue")

            # Setup file system watcher
            handler = ImageChangeHandler(directory.id, directory.path, self.embedders)
            watch = self.observer.schedule(handler, path, recursive=True)
            self.handlers[path] = (handler, watch)
            logger.info(f"Started filesystem monitoring for {path}")

            return directory.id

        except Exception as e:
            logger.error(f"Error adding directory {path}: {str(e)}", exc_info=True)
            session.rollback()
            raise RuntimeError(f"Error adding directory: {e}")
        finally:
            session.close()

    def _add_to_index_queue(self, directory_id: int, path: str, priority=0):
        with self.queue_lock:
            if (directory_id, path) not in self.processing_paths:
                self.index_queue.put((priority, (directory_id, path)))
                self.processing_paths.add((directory_id, path))
                self.index_workers.submit(self._process_index_queue)


    def _process_index_queue(self):
        while not self.index_queue.empty():
            try:
                priority, (directory_id, path) = self.index_queue.get_nowait()
                self._background_directory_indexing(directory_id, path)
            finally:
                with self.queue_lock:
                    self.processing_paths.discard((directory_id, path))

    def _background_directory_indexing(self, directory_id: int, dir_path: str):
        """Background indexing process for a directory"""
        logger.info(f"Starting background indexing for directory {dir_path} (ID: {directory_id})")
        session = SessionLocal()
        try:
            non_indexed_images = session.query(Image).filter(
                Image.directory_id == directory_id,
                Image.is_indexed == False
            ).all()

            total_images = len(non_indexed_images)
            if total_images == 0:
                logger.info(f"No images to index in directory {dir_path}")
                return

            logger.info(f"Found {total_images} unindexed images in directory {dir_path}")
            batch_size = settings.directory.batch_size
            processed = 0

            for i in range(0, len(non_indexed_images), batch_size):
                batch = non_indexed_images[i:i + batch_size]
                batch_paths = [img.path for img in batch]
                logger.debug(f"Processing batch {i // batch_size + 1} with {len(batch)} images")

                embeddings = self._compute_batch_embeddings(batch_paths)
                logger.debug(f"Computed embeddings for {len(embeddings)} images")

                # Update Milvus and mark as indexed
                for img_path, emb_dict in embeddings.items():
                    image = session.query(Image).filter(Image.path == img_path).first()
                    if image:
                        image.is_indexed = True

                session.commit()

            # Mark directory as fully indexed
            directory = session.query(Directory).get(directory_id)
            directory.is_indexed = True
            session.commit()
            logger.info(f"Completed indexing for directory {dir_path}. Marked as indexed.")

        except Exception as e:
            logger.error(f"Background indexing failed for directory {dir_path}: {str(e)}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def start(self):
        """
        Start indexer by queueing background indexing for all tracked directories
        """
        logger.info("Starting ImageIndexer service")

        session = SessionLocal()
        try:
            # Retrieve all tracked directories
            directories = session.query(Directory).all()
            logger.info(f"Found {len(directories)} tracked directories")

            for directory in directories:
                if not os.path.exists(directory.path):
                    # Remove directory if path no longer exists
                    logger.warning(f"Directory path missing: {directory.path}. Removing from tracking.")
                    self.remove_directory(directory.path)
                    continue

                # Queue background indexing
                logger.debug(f"Initializing directory {directory.path} (ID: {directory.id})")
                threading.Thread(
                    target=self._background_directory_indexing,
                    args=(directory.id, directory.path),
                    daemon=True
                ).start()

                # Setup file system watcher
                handler = ImageChangeHandler(directory.id, directory.path, self.embedders)
                watch = self.observer.schedule(handler, directory.path, recursive=True)
                self.handlers[directory.path] = (handler, watch)

            # Start watching all directories
            self.start_watching()
            self._start_consistency_checker()
            logger.info("Started filesystem observers and consistency checker")
        except Exception as e:
            logger.error(f"Indexer initialization failed: {str(e)}", exc_info=True)
        finally:
            session.close()

    def remove_directory(self, path: str):
        """
        Remove directory from monitoring and delete its indexed data

        Args:
            path (str): Directory path to remove
        """
        logger.info(f"Removing directory: {path}")
        session = SessionLocal()
        try:
            directory = session.query(Directory).filter(Directory.path == path).first()
            if directory:
                # Remove from Milvus
                logger.debug(f"Deleting Milvus entries for directory ID {directory.id}")
                for embedder_name in self.embedders.keys():
                    collection = Collection(embedder_name)
                    result = collection.delete(f"directory_id == {directory.id}")
                    logger.info(f"Deleted {result.delete_count} entries from {embedder_name} collection")
                    collection.flush()

                # Remove from database
                session.query(Image).filter(Image.directory_id == directory.id).delete()
                session.delete(directory)
                session.commit()

            # Stop watching
            if path in self.handlers:
                handler, watch = self.handlers[path]
                self.observer.unschedule(watch)
                del self.handlers[path]
                logger.debug(f"Stopped filesystem monitoring for {path}")

        except Exception as e:
            logger.error(f"Error removing directory {path}: {str(e)}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def _background_index(self, path: str, directory_id: int):
        """
        Background indexing process for a directory

        Args:
            path (str): Directory path
            directory_id (int): Directory database ID
        """

        session = SessionLocal()
        try:
            image_paths = self._get_image_paths(path)
            self._index_images(session, directory_id, image_paths)
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

    def _index_images(self, session: Session, directory_id: int, image_paths: List[str]):
        """
        Index images in batches using GPU
        """
        logger.info(f"Indexing {len(image_paths)} images for directory ID {directory_id}")

        batch_size = settings.directory.batch_size
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i + batch_size]
            logger.debug(f"Processing batch {i // batch_size + 1} with {len(batch)} images")

            embeddings = self._compute_batch_embeddings(batch)
            logger.debug(f"Computed embeddings for {len(embeddings)} images in batch")

            # Group embeddings by embedder
            embedder_data = defaultdict(list)
            for path, emb_dict in embeddings.items():
                existing = session.query(Image).filter(Image.path == path).first()
                if not existing:
                    image = Image(path=path, directory_id=directory_id, is_indexed=False)
                    session.add(image)

                for embedder_name, embedding in emb_dict.items():
                    embedder_data[embedder_name].append({
                        "directory_id": directory_id,
                        "image_path": path,
                        "embedding": embedding
                    })

            # Batch insert to Milvus
            for embedder_name, data in embedder_data.items():
                collection = Collection(embedder_name)
                collection.insert(data)
                collection.flush()
                logger.info(f"Inserted {len(data)} embeddings into {embedder_name} collection")

            # Mark images as indexed after successful Milvus insertion
            for path in embeddings.keys():
                image = session.query(Image).filter(Image.path == path).first()
                if image:
                    image.is_indexed = True

            session.commit()
            logger.debug(f"Completed processing batch {i // batch_size + 1}")

    def _compute_batch_embeddings(self, image_paths: List[str]) -> Dict[str, Dict[str, List[float]]]:
        """
        Compute embeddings for a batch of images using available GPUs

        Args:
            image_paths (List[str]): Paths of images to embed

        Returns:
            Dict with image paths and their embeddings
        """
        logger.debug(f"Computing embeddings for {len(image_paths)} images")
        embeddings = {}
        success_count = 0
        fail_count = 0
        with ThreadPoolExecutor(max_workers=settings.directory.num_embedding_workers) as executor:
            futures = {
                executor.submit(self._embed_single_image, path): path
                for path in image_paths
            }

            for future in as_completed(futures):
                path = futures[future]
                try:
                    embeddings[path] = future.result()
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    logger.error(f"Failed to embed {path}: {str(e)}", exc_info=True)

        logger.info(f"Embedding complete: {success_count} successes, {fail_count} failures")
        return embeddings

    def _embed_single_image(self, image_path: str) -> Dict[str, List[float]]:
        """
        Embed a single image using all available embedders

        Args:
            image_path (str): Path to image file

        Returns:
            Dict of embedder names and their embeddings
        """
        image = PImage.open(image_path).convert("RGB")
        return {
            name: embedder.embed(image)
            for name, embedder in self.embedders.items()
        }

    def start_watching(self):
        """Start file system monitoring"""
        thread = threading.Thread(target=self._run_observer, daemon=True)
        thread.start()

    def _run_observer(self):
        """Run file system observer"""
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def _start_consistency_checker(self):
        def run():
            while True:
                time.sleep(self.consistency_check_interval)
                self.run_consistency_check()

        threading.Thread(target=run, daemon=True).start()

    def run_consistency_check(self):
        logger.info("Starting system-wide consistency check")
        session = SessionLocal()
        try:
            directories = session.query(Directory).all()
            logger.info(f"Checking consistency for {len(directories)} directories")
            for directory in directories:
                self._check_directory_consistency(session, directory)

            logger.info("Completed system-wide consistency check")
        except Exception as e:
            logger.error(f"Consistency check failed: {str(e)}", exc_info=True)

        finally:
            session.close()

    def _check_directory_consistency(self, session: Session, directory: Directory):
        logger.info(f"Checking consistency for directory {directory.path} (ID: {directory.id})")
        # Check directory existence
        if not os.path.exists(directory.path):
            logger.warning(f"Directory path missing: {directory.path}. Removing from system.")
            self.remove_directory(directory.path)
            return

        # Get current filesystem state
        fs_paths = set(self._get_image_paths(directory.path))

        # Get database state
        db_images = session.query(Image).filter(
            Image.directory_id == directory.id
        ).all()
        db_paths = {img.path for img in db_images}

        # Find discrepancies
        new_paths = fs_paths - db_paths
        deleted_paths = db_paths - fs_paths

        logger.info(f"Consistency check results for {directory.path}:")
        logger.info(f" - New files detected: {len(new_paths)}")
        logger.info(f" - Missing files detected: {len(deleted_paths)}")

        # Handle new files
        for path in new_paths:
            if not session.query(Image).filter(Image.path == path).first():
                session.add(Image(
                    path=path,
                    directory_id=directory.id,
                    is_indexed=False
                ))
        session.commit()

        # Handle deleted files
        for path in deleted_paths:
            image = session.query(Image).filter(Image.path == path).first()
            if image:
                # Remove from Milvus
                for embedder_name in self.embedders.keys():
                    collection = Collection(embedder_name)
                    collection.delete(f"image_path == '{path}'")
                    collection.flush()
                # Remove from DB
                session.delete(image)
        session.commit()

        # Verify Milvus consistency
        indexed_images = session.query(Image).filter(
            Image.directory_id == directory.id,
            Image.is_indexed == True
        ).all()

        # Check against Milvus
        for embedder_name in self.embedders.keys():
            collection = Collection(embedder_name)
            try:
                # Get all expected paths for this directory
                expected_paths = {img.path for img in indexed_images}

                # Batch query Milvus in pages
                milvus_paths = set()
                query_iterator = collection.query_iterator(
                    expr=f"directory_id == {directory.id}",
                    output_fields=["image_path"],
                    batch_size=1000
                )

                while True:
                    res = query_iterator.next()
                    if not res:
                        break
                    milvus_paths.update(item["image_path"] for item in res)

                # Find discrepancies
                missing_paths = expected_paths - milvus_paths
                extra_paths = milvus_paths - expected_paths

                logger.info(f"Milvus ({embedder_name}) consistency:")
                logger.info(f" - Missing entries: {len(missing_paths)}")
                logger.info(f" - Extra entries: {len(extra_paths)}")

                # Handle missing entries
                if missing_paths:
                    session.query(Image).filter(
                        Image.path.in_(missing_paths)
                    ).update({Image.is_indexed: False})
                    session.commit()
                    self._background_directory_indexing(directory.id, directory.path)

                # Handle extra entries (orphaned in Milvus)
                if extra_paths:
                    for path in extra_paths:
                        collection.delete(f"directory_id == {directory.id} && image_path == '{path}'")
                    collection.flush()

            except Exception as e:
                logger.error(f"Milvus query failed for {embedder_name}: {str(e)}", exc_info=True)


class ImageChangeHandler(FileSystemEventHandler):
    def __init__(self, directory_id: int, directory_path: str, embedders: Dict):
        self.directory_id = directory_id
        self.directory_path = directory_path
        self.embedders = embedders
        logger.debug(f"Created handler for directory {directory_path} (ID: {directory_id})")

    def on_created(self, event):
        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"Detected new image: {event.src_path}")
            self._handle_new_image(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"Detected deleted image: {event.src_path}")
            self._handle_deleted_image(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"Detected modified image: {event.src_path}")
            self._handle_modified_image(event.src_path)

    def on_moved(self, event):
        src_path = event.src_path
        dest_path = event.dest_path

        if not event.is_directory and self._is_image(dest_path):
            logger.info(f"Detected moved image: {src_path} -> {dest_path}")
            # Check if moved within same directory
            dest_dir = os.path.dirname(dest_path)
            if os.path.commonpath([dest_dir, self.directory_path]) == self.directory_path:
                self._handle_moved_image(src_path, dest_path)
            else:
                # Handle as deletion from original directory
                self._handle_deleted_image(src_path)

    def _is_image(self, path: str) -> bool:
        return path.lower().endswith(('.png', '.jpg', '.jpeg'))

    def _handle_new_image(self, path: str):
        session = SessionLocal()
        try:
            existing = session.query(Image).filter(Image.path == path).first()
            if not existing:
                logger.debug(f"Creating new database entry for {path}")
                # Create image record
                image = Image(path=path, directory_id=self.directory_id, is_indexed=False)
                session.add(image)
                session.commit()
                logger.info(f"Added new image to database: {path}")
                indexer = ImageIndexer()
                indexer._add_to_index_queue(self.directory_id, path, priority=0)
                logger.debug(f"Added new image to indexing queue: {path}")

        except Exception as e:
            logger.error(f"Error handling new image {path}: {str(e)}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def _handle_deleted_image(self, path: str):
        session = SessionLocal()
        try:
            image = session.query(Image).filter(Image.path == path).first()
            if image:
                for embedder_name in self.embedders.keys():
                    collection = Collection(embedder_name)
                    collection.delete(f"image_path == '{path}'")
                    collection.flush()
                session.delete(image)
                session.commit()
        finally:
            session.close()

    def _handle_modified_image(self, path: str):
        session = SessionLocal()
        try:
            image = session.query(Image).filter(Image.path == path).first()
            if image and image.is_indexed:
                logger.info(f"Re-indexing modified image: {path}")
                # Mark as unindexed and delete existing embeddings
                image.is_indexed = False

                # Batch delete from Milvus
                for embedder_name in self.embedders.keys():
                    collection = Collection(embedder_name)
                    result = collection.delete(f"directory_id == {self.directory_id} && image_path == '{path}'")
                    logger.info(f"Removed {result.delete_count} embeddings from {embedder_name} for {path}")
                    collection.flush()

                session.commit()

                # Queue for re-indexing
                indexer = ImageIndexer.instance()
                indexer._background_directory_indexing(self.directory_id, self.directory_path)

        except Exception as e:
            session.rollback()
            print(f"Error handling modified image {path}: {e}")
        finally:
            session.close()

    def _handle_moved_image(self, src_path: str, dest_path: str):
        session = SessionLocal()
        try:
            image = session.query(Image).filter(Image.path == src_path).first()
            if image:
                # Batch update Milvus entries
                move_data = []
                for embedder_name in self.embedders.keys():
                    collection = Collection(embedder_name)
                    # Batch retrieve and delete
                    res = collection.query(
                        expr=f"directory_id == {self.directory_id} and image_path == '{src_path}'",
                        output_fields=["embedding"]
                    )
                    if res:
                        move_data.extend([{
                            "embedder": embedder_name,
                            "embeddings": [item["embedding"] for item in res]
                        }])
                        collection.delete(f"directory_id == {self.directory_id} and image_path == '{src_path}'")

                # Batch insert new entries
                for data in move_data:
                    collection = Collection(data["embedder"])
                    collection.insert([{
                        "directory_id": self.directory_id,
                        "image_path": dest_path,
                        "embedding": emb
                    } for emb in data["embeddings"]])
                    collection.flush()

                # Update database after successful Milvus operations
                image.path = dest_path
                session.commit()

        except Exception as e:
            session.rollback()
            print(f"Error handling moved image {src_path}: {e}")
        finally:
            session.close()
