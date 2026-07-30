from monitoring import logger

from typing import Dict, List, Set

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
        """Remove a directory and everything tracked under it.

        The ORM relationship has no cascade, so deleting the row on its own used
        to strand every Image belonging to it (and, with them, rows in the
        vector tables that nothing would ever clean up).
        """
        directory_id = directory.id
        VectorRepository().delete_directory_all_embedders(directory_id)
        self.session.query(Image).filter(Image.directory_id == directory_id).delete(
            synchronize_session=False
        )
        self.session.delete(directory)
        self.session.commit()
        logger.info(f"Removed directory {directory_id} and its tracked images")


class ImageRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_path(self, path: str) -> Image:
        return self.session.query(Image).filter(Image.path == path).first()

    def get_paths(self, directory_id: int) -> Set[str]:
        """Every known path for a directory, as a set for cheap diffing."""
        rows = self.session.query(Image.path).filter(Image.directory_id == directory_id).all()
        return {row[0] for row in rows}

    def add_new_images(self, directory_id: int, image_paths: List[str]) -> int:
        """Insert the paths that aren't tracked yet and return how many were added.

        Existing paths are found with a single query instead of one lookup per
        path: adding a folder of 10k images used to issue 10k SELECTs.
        """
        paths = list(dict.fromkeys(image_paths))
        if not paths:
            return 0

        known: Set[str] = set()
        # SQLite caps the number of variables per statement (999 by default), so
        # the IN clause has to be chunked.
        for start in range(0, len(paths), 500):
            chunk = paths[start:start + 500]
            rows = self.session.query(Image.path).filter(Image.path.in_(chunk)).all()
            known.update(row[0] for row in rows)

        new_paths = [p for p in paths if p not in known]
        if new_paths:
            self.session.bulk_save_objects([
                Image(path=p, directory_id=directory_id, is_indexed=False)
                for p in new_paths
            ])
            self.session.commit()
        logger.info(f"Added {len(new_paths)} new images to database for directory {directory_id}")
        return len(new_paths)

    def get_unindexed_images(self, directory_id: int) -> List[Image]:
        return self.session.query(Image).filter(
            Image.directory_id == directory_id,
            Image.is_indexed == False
        ).all()

    def delete(self, image: Image):
        self.session.delete(image)
        self.session.commit()

    def delete_by_paths(self, paths: List[str]) -> int:
        """Bulk-delete image rows by path (one statement per chunk)."""
        paths = [p for p in dict.fromkeys(paths) if p]
        if not paths:
            return 0
        deleted = 0
        for start in range(0, len(paths), 500):
            chunk = paths[start:start + 500]
            deleted += self.session.query(Image).filter(Image.path.in_(chunk)).delete(
                synchronize_session=False
            )
        self.session.commit()
        return deleted

    def mark_unindexed(self, paths: List[str]) -> int:
        """Flag paths for re-embedding without loading the ORM objects."""
        paths = [p for p in dict.fromkeys(paths) if p]
        if not paths:
            return 0
        updated = 0
        for start in range(0, len(paths), 500):
            chunk = paths[start:start + 500]
            updated += self.session.query(Image).filter(Image.path.in_(chunk)).update(
                {Image.is_indexed: False}, synchronize_session=False
            )
        self.session.commit()
        return updated


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

    def delete_by_paths(self, embedder_name: str, image_paths: List[str]):
        count = self._store.delete_by_paths(embedder_name, image_paths)
        if count:
            logger.info(f"Deleted vectors for {count} path(s) in table '{embedder_name}'")

    def delete_paths_all_embedders(self, image_paths: List[str]):
        """Drop vectors for these paths from every embedder table.

        Embedder names are resolved at call time: the manager swaps its dict
        when models are reloaded (profile change, GPU toggle), so a cached copy
        would eventually point at the wrong tables.
        """
        from core import embedder_manager

        paths = [p for p in dict.fromkeys(image_paths) if p]
        if not paths:
            return
        for embedder_name in embedder_manager.get_image_embedders():
            try:
                self._store.delete_by_paths(embedder_name, paths)
            except Exception as exc:
                logger.error(f"Failed to delete vectors from '{embedder_name}': {exc}", exc_info=True)

    def delete_directory_all_embedders(self, directory_id: int):
        from core import embedder_manager

        for embedder_name in embedder_manager.get_image_embedders():
            try:
                self._store.delete_by_directory(embedder_name, directory_id)
            except Exception as exc:
                logger.error(f"Failed to clear vectors from '{embedder_name}': {exc}", exc_info=True)

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