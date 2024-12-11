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
                # Directory is already indexed, so we need to embed this single new image now
                image = PImage.open(image_path).convert("RGB")
                # For a single image, just do a quick embedding and insert
                for embedder_name, embedder in self.embedders.items():
                    embedding = embedder.embed(image)
                    collection_name = f"{embedder_name}"
                    collection = Collection(name=collection_name)
                    # Insert single image
                    collection.insert([{
                        "directory_id": self.directory_id,
                        "image_path": image_path,
                        "embedding": embedding
                    }])
                    # Flush once after all embedders are processed to reduce overhead
                for embedder_name in self.embedders.keys():
                    collection_name = f"{embedder_name}"
                    collection = Collection(name=collection_name)
                    collection.flush()

                # Mark the image as indexed
                image_record.is_indexed = True
                session.commit()

    def remove_image(self, image_path):
        session = SessionLocal()
        image_record = session.query(Image).filter(Image.path == image_path).first()
        if image_record:
            session.delete(image_record)
            session.commit()

        for embedder_name in self.embedders.keys():
            collection_name = f"{embedder_name}"
            collection = Collection(name=collection_name)
            collection.delete(expr=f"image_path == '{image_path}'")
            # Defer flushes until after loop if desired
        for embedder_name in self.embedders.keys():
            collection_name = f"{embedder_name}"
            collection = Collection(name=collection_name)
            collection.flush()


def rename_path(path):
    return path.replace("/", "_").replace("\\", "_")


@Singleton
class DirectoryWatcher:
    def __init__(self):
        self.observer = Observer()
        self.handlers = {}
        self.watches = {}
        self.executor = ThreadPoolExecutor(max_workers=settings.app.num_watcher_workers)

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

        self.executor.submit(self._process_directory_in_background, path, directory_id)

        handler = ImageChangeHandler(directory_id)
        self.handlers[renamed_path] = handler
        watch = self.observer.schedule(handler, path, recursive=settings.app.recursive_indexing)
        self.watches[renamed_path] = watch

        session.close()

    def _process_directory_in_background(self, path, directory_id):
        """Embed images of the directory in a background thread, set is_indexed=True when done if not already."""
        session = SessionLocal()
        directory_record = session.query(Directory).filter(Directory.id == directory_id).first()

        # 1. Sync all images in the DB first
        existing_images = set(
            img.path for img in session.query(Image.path).filter(Image.directory_id == directory_id).all())

        # Add any new images not in DB
        # TODO: os.walk traverses recursively, we should traverse recursively or not by the value of setting.app.recursive_indexing
        to_add = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    full_path = os.path.join(root, file)
                    if full_path not in existing_images:
                        to_add.append(Image(path=full_path, directory_id=directory_id, is_indexed=False))

        if to_add:
            session.bulk_save_objects(to_add)
            session.commit()

        # 2. Retrieve all images for the directory
        images = session.query(Image).filter(Image.directory_id == directory_id).all()
        not_indexed_images = [img for img in images if not img.is_indexed]

        if not not_indexed_images:
            # If no images need indexing, just mark the directory as indexed and return
            directory_record.is_indexed = True
            session.commit()
            return

        embedders = embedder_manager.get_image_embedders()

        # 3. Process embeddings in parallel
        # We'll do:
        # - Load all images
        # - Embed in parallel
        # - Batch insert into Milvus
        futures = []
        with ThreadPoolExecutor(max_workers=settings.app.num_embedding_workers) as pool:
            for img_record in not_indexed_images:
                if os.path.exists(img_record.path):
                    # Submit a job to embed this image once per embedder, or embed once and store results
                    # We only load the image once here:
                    futures.append(pool.submit(self._embed_image, img_record.path, embedders))

        # Gather results as [ (path, {embedder_name: embedding}) ]
        all_embeddings = []
        for f in as_completed(futures):
            result = f.result()
            if result is not None:
                all_embeddings.append(result)

        # 4. Batch insert into Milvus
        # Organize embeddings by embedder to do bulk inserts
        embedder_collections_data = {name: {"directory_id": [], "image_path": [], "embedding": []}
                                     for name in embedders.keys()}

        count = 0
        for (img_path, embeddings_dict) in all_embeddings:
            for embedder_name, emb in embeddings_dict.items():
                embedder_collections_data[embedder_name]["directory_id"].append(directory_id)
                embedder_collections_data[embedder_name]["image_path"].append(img_path)
                embedder_collections_data[embedder_name]["embedding"].append(emb)
            count += 1
            # If we reach a batch size, flush to Milvus and then continue
            if count % settings.app.batch_size == 0:
                self._batch_insert_to_milvus(embedder_collections_data)
                # Reset for next batch
                embedder_collections_data = {name: {"directory_id": [], "image_path": [], "embedding": []}
                                             for name in embedders.keys()}

        # Insert any remaining
        if embedder_collections_data[embedders.keys().__iter__().__next__()]["directory_id"]:
            self._batch_insert_to_milvus(embedder_collections_data)

        # 5. Mark all these images as indexed in one go
        indexed_paths = [record[0] for record in all_embeddings]
        if indexed_paths:
            session.query(Image).filter(Image.path.in_(indexed_paths)).update({"is_indexed": True},
                                                                              synchronize_session=False)
            session.commit()

        # 6. Check if all images are indexed now
        images = session.query(Image).filter(Image.directory_id == directory_id).all()
        if all(img.is_indexed for img in images):
            directory_record.is_indexed = True
            session.commit()

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

    def _batch_insert_to_milvus(self, embedder_collections_data):
        # Insert data for each embedder in one go
        for embedder_name, data in embedder_collections_data.items():
            if not data["directory_id"]:
                continue
            collection_name = f"{embedder_name}"
            collection = Collection(name=collection_name)
            # Insert bulk data
            entities = [
                data["directory_id"],
                data["image_path"],
                data["embedding"]
            ]
            # The order of fields must match the schema order
            collection.insert(entities)

        # Flush all collections after a bulk insert
        for embedder_name in embedder_collections_data.keys():
            collection_name = f"{embedder_name}"
            collection = Collection(name=collection_name)
            collection.flush()

    def remove_directory(self, path):
        session = SessionLocal()

        renamed_path = rename_path(path)

        directory_record = session.query(Directory).filter(Directory.path == path).first()

        if directory_record:
            for embedder_name in embedder_manager.get_image_embedders().keys():
                collection_name = f"{embedder_name}"
                collection = Collection(name=collection_name)
                # Delete all images for this directory in one go
                collection.delete(expr=f"directory_id == {directory_record.id}")
            # Flush once after all deletions
            for embedder_name in embedder_manager.get_image_embedders().keys():
                collection_name = f"{embedder_name}"
                collection = Collection(name=collection_name)
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
            index_params = {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 48, "efConstruction": 200}
            }
            collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
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
