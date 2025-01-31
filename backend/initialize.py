from pymilvus import connections
from pymilvus import utility, FieldSchema, CollectionSchema, DataType, Collection

from core import EmbedderManager
from database.database_manager import SessionLocal, Directory
from monitoring import directory_watcher
from settings import settings


def connect_to_milvus():
    connections.connect("default", host=settings.milvus.host, port=settings.milvus.port)


def create_collection_for_embedder(collection_name, embedder):
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


def initialize():
    connect_to_milvus()

    embedders = EmbedderManager.instance().get_image_embedders()

    for embedder_name, embedder in embedders.items():
        collection_name = f"{embedder_name}"
        create_collection_for_embedder(collection_name, embedder)

    directory_watcher.start()

    session = SessionLocal()
    directories = session.query(Directory).all()
    for directory in directories:
        directory_watcher.add_directory(directory.path)
