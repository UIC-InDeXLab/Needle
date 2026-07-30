"""Embedded on-disk vector store backed by LanceDB.

This module replaces the previous Milvus-based vector database so that Needle can
run as a fully self-contained desktop application without any external services
(Milvus / etcd / MinIO). Each embedder gets its own LanceDB table whose rows have
the shape::

    {"image_path": str (unique), "directory_id": int, "embedding": float32[dim]}

Similarity search uses cosine distance, matching the previous Milvus behaviour.
"""

from typing import Dict, List, Optional, Sequence

import lancedb
import pyarrow as pa

from core.singleton import Singleton
from monitoring import logger
from settings import settings


def _sql_str(value: str) -> str:
    """Escape a string for safe interpolation into a LanceDB SQL filter."""
    return "'" + value.replace("'", "''") + "'"


@Singleton
class VectorStore:
    """LanceDB-backed vector store. One table per embedder."""

    def __init__(self):
        self._path = settings.storage.lancedb_path
        self._db = lancedb.connect(self._path)
        self._dims: Dict[str, int] = {}
        logger.info(f"Connected to LanceDB at {self._path}")

    # -- schema -----------------------------------------------------------
    def create_table(self, name: str, dim: int) -> None:
        self._dims[name] = dim
        if name in self._db.table_names():
            return
        schema = pa.schema(
            [
                pa.field("image_path", pa.utf8()),
                pa.field("directory_id", pa.int64()),
                pa.field("embedding", pa.list_(pa.float32(), dim)),
            ]
        )
        self._db.create_table(name, schema=schema)
        logger.info(f"Created LanceDB table '{name}' (dim={dim})")

    def _table(self, name: str):
        return self._db.open_table(name)

    # -- writes -----------------------------------------------------------
    def insert(self, name: str, entries: List[Dict]) -> None:
        if not entries:
            return
        rows = [
            {
                "image_path": e["image_path"],
                "directory_id": int(e["directory_id"]),
                "embedding": [float(x) for x in e["embedding"]],
            }
            for e in entries
        ]
        self._table(name).add(rows)
        logger.debug(f"Inserted {len(rows)} rows into LanceDB table '{name}'")

    def delete_by_path(self, name: str, image_path: str) -> None:
        self._table(name).delete(f"image_path = {_sql_str(image_path)}")

    def delete_by_paths(self, name: str, image_paths: Sequence[str]) -> int:
        """Delete many paths in as few table rewrites as possible.

        Every ``delete`` rewrites the table's manifest, so deleting a thousand
        removed files one call at a time is dramatically slower than a handful
        of ``IN (...)`` predicates. The batch size keeps the generated filter
        well inside any expression-length limits.
        """
        paths = [p for p in dict.fromkeys(image_paths) if p]
        if not paths:
            return 0
        table = self._table(name)
        batch = 500
        for start in range(0, len(paths), batch):
            chunk = paths[start:start + batch]
            predicate = ", ".join(_sql_str(p) for p in chunk)
            table.delete(f"image_path IN ({predicate})")
        return len(paths)

    def delete_by_directory(self, name: str, directory_id: int) -> None:
        self._table(name).delete(f"directory_id = {int(directory_id)}")

    # -- reads ------------------------------------------------------------
    def get_embeddings_by_path(self, name: str, image_path: str) -> List[List[float]]:
        dataset = self._table(name).to_lance()
        table = dataset.to_table(
            columns=["embedding"], filter=f"image_path = {_sql_str(image_path)}"
        )
        return [row.as_py() for row in table.column("embedding")]

    def list_all_paths(self, name: str) -> List[str]:
        dataset = self._table(name).to_lance()
        table = dataset.to_table(columns=["image_path"])
        return [row.as_py() for row in table.column("image_path")]

    def search(
        self,
        name: str,
        vector: Sequence[float],
        limit: int,
        directory_ids: Optional[Sequence[int]] = None,
    ) -> List[str]:
        query = (
            self._table(name)
            .search([float(x) for x in vector])
            .metric("cosine")
        )
        if directory_ids:
            ids = ", ".join(str(int(i)) for i in directory_ids)
            query = query.where(f"directory_id IN ({ids})", prefilter=True)
        results = query.limit(limit).to_list()
        return [r["image_path"] for r in results]
