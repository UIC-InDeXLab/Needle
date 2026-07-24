from core import embedder_manager
from core.vector_store import VectorStore
from indexing import image_indexing_service
from models import models  # noqa: F401  (ensures SQLite tables are created)
from monitoring import logger


def initialize():
    """Boot the embedded stores and start the indexing pipeline.

    Replaces the previous Milvus/etcd/MinIO + PostgreSQL setup with a fully
    self-contained SQLite (metadata) + LanceDB (vectors) stack.
    """
    vector_store = VectorStore.instance()

    embedders = embedder_manager.get_image_embedders()
    for embedder_name, embedder in embedders.items():
        vector_store.create_table(embedder_name, embedder.embedding_dim)

    logger.info("Embedded stores initialized; starting indexing service")
    image_indexing_service.start()

