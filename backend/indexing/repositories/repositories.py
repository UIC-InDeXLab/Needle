from monitoring import logger

from typing import Dict, List

from sqlalchemy.orm import Session

from core.vector_store import VectorStore
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


class VectorRepository:
    """Access layer for the embedded LanceDB vector store.

    One table per embedder; rows are {image_path, directory_id, embedding}.
    """

    def __init__(self):
        self._store = VectorStore.instance()

    def insert_entries(self, embedder_name: str, entries: List[Dict]):
        self._store.insert(embedder_name, entries)
        logger.debug(f"Inserted {len(entries)} entries into vector table '{embedder_name}'")

    def delete_by_path(self, embedder_name: str, image_path: str):
        self._store.delete_by_path(embedder_name, image_path)
        logger.info(f"Deleted vectors for path '{image_path}' in table '{embedder_name}'")

    def delete_by_directory(self, embedder_name: str, directory_id: int):
        self._store.delete_by_directory(embedder_name, directory_id)
        logger.info(f"Deleted vectors for directory {directory_id} in table '{embedder_name}'")

    def get_embeddings_by_path(self, embedder_name: str, image_path: str) -> List[List[float]]:
        return self._store.get_embeddings_by_path(embedder_name, image_path)

    def list_all_paths(self, embedder_name: str) -> List[str]:
        return self._store.list_all_paths(embedder_name)

    def search(self, embedder_name: str, vector, limit: int, directory_ids=None) -> List[str]:
        return self._store.search(embedder_name, vector, limit, directory_ids)


# Backwards-compatible alias for existing imports.
MilvusRepository = VectorRepository