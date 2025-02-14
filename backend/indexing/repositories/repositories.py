from monitoring import logger

from typing import List, Dict

from pymilvus import Collection
from sqlalchemy.orm import Session

from models.models import Directory, Image


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
        # collection.flush()
        logger.info(f"Deleted {result.delete_count} entries in Milvus collection '{embedder_name}' using expr {expr}")
        return result

    def insert_entries(self, embedder_name: str, entries: List[Dict]):
        collection = Collection(embedder_name)
        collection.insert(entries)
        # collection.flush()
        logger.debug(f"Inserted {len(entries)} entries into Milvus collection '{embedder_name}'")

    def query_entries(self, embedder_name: str, expr: str, output_fields: List[str], batch_size: int = 1000):
        collection = Collection(embedder_name)
        return collection.query_iterator(expr=expr, output_fields=output_fields, batch_size=batch_size)

    def flush(self, embedder_name: str):
        collection = Collection(embedder_name)
        collection.flush()