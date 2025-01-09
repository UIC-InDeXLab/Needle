import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image as PImage
from pymilvus import utility, FieldSchema, CollectionSchema, DataType, Collection
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from core import embedder_manager
from core.singleton import Singleton
from database import SessionLocal, Directory, Image
from settings import settings


class ImageChangeHandler(FileSystemEventHandler):
    def __init__(self, directory_id):
        self.directory_id = directory_id
        self.embedders = embedder_manager.get_image_embedders()

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.add_image(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.remove_image(event.src_path)

    def add_image(self, image_path):
        session = SessionLocal()
        existing_image = session.query(Image).filter(Image.path == image_path).first()
        if not existing_image:
            image_record = Image(path=image_path, directory_id=self.directory_id, is_indexed=False)
            session.add(image_record)
            session.commit()

            dir_record = session.query(Directory).filter(Directory.id == self.directory_id).first()
            if dir_record.is_indexed:
                # Directory is already indexed, so index this single new image now.
                image = PImage.open(image_path).convert("RGB")
                for embedder_name, embedder in self.embedders.items():
                    embedding = embedder.embed(image)
                    collection = Collection(name=embedder_name)
                    collection.insert([{
                        "directory_id": self.directory_id,
                        "image_path": image_path,
                        "embedding": embedding
                    }])
                for embedder_name in self.embedders.keys():
                    collection = Collection(name=embedder_name)
                    collection.flush()

                image_record.is_indexed = True
                session.commit()
        session.close()

    def remove_image(self, image_path):
        session = SessionLocal()
        image_record = session.query(Image).filter(Image.path == image_path).first()
        if image_record:
            session.delete(image_record)
            session.commit()

        for embedder_name in self.embedders.keys():
            collection = Collection(name=embedder_name)
            collection.delete(expr=f"image_path == '{image_path}'")

        for embedder_name in self.embedders.keys():
            collection = Collection(name=embedder_name)
            collection.flush()
        session.close()


def rename_path(path):
    return path.replace("/", "_").replace("\\", "_")


@Singleton
class DirectoryWatcher:
    def __init__(self):
        self.observer = Observer()
        self.handlers = {}
        self.watches = {}
        self.executor = ThreadPoolExecutor(max_workers=settings.directory.num_watcher_workers)

    def add_directory(self, path):
        session = SessionLocal()
        if not os.path.exists(path):
            raise FileNotFoundError(f"The path {path} does not exist.")

        renamed_path = rename_path(path)

        existing_directory = session.query(Directory).filter(Directory.path == path).first()
        if not existing_directory:
            directory_record = Directory(path=path, is_indexed=False)
            session.add(directory_record)
            session.commit()
            directory_id = directory_record.id
        else:
            directory_id = existing_directory.id
            existing_directory.is_indexed = False
            session.commit()

        handler = ImageChangeHandler(directory_id)
        self.handlers[renamed_path] = handler
        watch = self.observer.schedule(handler, path, recursive=settings.directory.recursive_indexing)
        self.watches[renamed_path] = watch

        # Start the background indexing
        self.executor.submit(self._process_directory_in_background, path, directory_id)

        session.close()
        return directory_id

    def _process_directory_in_background(self, path, directory_id):
        """Embed images of the directory in a background thread, processing them in batches.
           For each batch:
           1. Find a batch of not-indexed images.
           2. Compute their embeddings in parallel.
           3. Insert the embeddings into Milvus and update Postgres.
           4. Repeat until all images are indexed.
        """
        session = SessionLocal()
        directory_record = session.query(Directory).filter(Directory.id == directory_id).first()

        # 1. Sync all images in the DB
        existing_images = set(
            img.path for img in session.query(Image.path).filter(Image.directory_id == directory_id).all()
        )

        to_add = []
        if settings.directory.recursive_indexing:  # If recursive search is required
            for root, _, files in os.walk(path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        full_path = os.path.join(root, file)
                        if full_path not in existing_images:
                            to_add.append(Image(path=full_path, directory_id=directory_id, is_indexed=False))
        else:  # Non-recursive search
            for file in os.listdir(path):
                full_path = os.path.join(path, file)
                if os.path.isfile(full_path) and file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    if full_path not in existing_images:
                        to_add.append(Image(path=full_path, directory_id=directory_id, is_indexed=False))

        if to_add:
            session.bulk_save_objects(to_add)
            session.commit()

        # 2. Retrieve all not indexed images
        embedders = embedder_manager.get_image_embedders()

        batch_size = settings.directory.batch_size
        while True:
            not_indexed_images = session.query(Image).filter(Image.directory_id == directory_id, Image.is_indexed == False).all()
            if not not_indexed_images:
                # All images are indexed
                directory_record.is_indexed = True
                session.commit()
                break

            # Process images in batches
            batch = not_indexed_images[:batch_size]

            # 3. Embed images in parallel for this batch
            with ThreadPoolExecutor(max_workers=settings.directory.num_embedding_workers) as pool:
                futures = {pool.submit(self._embed_image, img_record.path, embedders): img_record.path for img_record in batch}

                embeddings_batch = []
                for f in as_completed(futures):
                    result = f.result()
                    if result is not None:
                        embeddings_batch.append(result)

            # 4. Insert embeddings for this batch and update DB
            if embeddings_batch:
                self._insert_embeddings_batch(session, directory_id, embeddings_batch, embedders)

        session.close()

    def _embed_image(self, image_path, embedders):
        # Load image once
        if not os.path.exists(image_path):
            return None
        with PImage.open(image_path).convert("RGB") as img:
            result = {}
            # Compute embeddings for all embedders
            for embedder_name, embedder in embedders.items():
                embedding = embedder.embed(img)
                result[embedder_name] = embedding
            return (image_path, result)

    def _insert_embeddings_batch(self, session, directory_id, embeddings_batch, embedders):
        """Insert a batch of embeddings into Milvus, update their DB records, and commit."""
        embedder_collections_data = {
            name: {"directory_id": [], "image_path": [], "embedding": []}
            for name in embedders.keys()
        }

        indexed_paths = []
        for (img_path, embeddings_dict) in embeddings_batch:
            indexed_paths.append(img_path)
            for embedder_name, emb in embeddings_dict.items():
                embedder_collections_data[embedder_name]["directory_id"].append(directory_id)
                embedder_collections_data[embedder_name]["image_path"].append(img_path)
                embedder_collections_data[embedder_name]["embedding"].append(emb)

        # Insert data for each embedder
        for embedder_name, data in embedder_collections_data.items():
            if data["directory_id"]:
                collection = Collection(name=embedder_name)
                entities = [
                    data["directory_id"],
                    data["image_path"],
                    data["embedding"]
                ]
                collection.insert(entities)

        # Flush all after batch insert
        for embedder_name in embedders.keys():
            collection = Collection(name=embedder_name)
            collection.flush()

        # Update DB to mark these images as indexed
        session.query(Image).filter(Image.path.in_(indexed_paths)).update({"is_indexed": True},
                                                                          synchronize_session=False)
        session.commit()

    def remove_directory(self, path):
        session = SessionLocal()

        renamed_path = rename_path(path)

        directory_record = session.query(Directory).filter(Directory.path == path).first()

        if directory_record:
            for embedder_name in embedder_manager.get_image_embedders().keys():
                collection = Collection(name=embedder_name)
                # Delete all images for this directory in one go
                collection.delete(expr=f"directory_id == {directory_record.id}")
            # Flush once after all deletions
            for embedder_name in embedder_manager.get_image_embedders().keys():
                collection = Collection(name=embedder_name)
                collection.flush()

            session.query(Image).filter(Image.directory_id == directory_record.id).delete()
            session.commit()

            session.delete(directory_record)
            session.commit()

        self.handlers.pop(renamed_path, None)
        watch = self.watches.pop(renamed_path, None)
        if watch:
            self.observer.unschedule(watch)
        session.close()

    def create_collection_for_embedder(self, collection_name, embedder):
        if not utility.has_collection(collection_name):
            fields = [
                FieldSchema(name="directory_id", dtype=DataType.INT64, is_primary=False),
                FieldSchema(name="image_path", dtype=DataType.VARCHAR, max_length=500, is_primary=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=embedder.embedding_dim)
            ]
            schema = CollectionSchema(fields=fields, description=f"Collection for embedder: {collection_name}")
            collection = Collection(name=collection_name, schema=schema)
            # TODO: Get index params from settings
            index_params = {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 48, "efConstruction": 200}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
        else:
            collection = Collection(name=collection_name)

        collection.load()

    def start(self):
        thread = threading.Thread(target=self._run_observer)
        thread.daemon = True
        thread.start()

    def _run_observer(self):
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def finalize(self):
        self.observer.stop()
