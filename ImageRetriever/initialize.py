from pymilvus import connections

from core import EmbedderManager
from database.database_manager import SessionLocal, Directory
from monitoring import directory_watcher
from settings import settings


def connect_to_milvus():
    connections.connect("default", host=settings.milvus.host, port=settings.milvus.port)


def initialize():
    connect_to_milvus()

    embedders = EmbedderManager.instance().get_image_embedders()

    for embedder_name, embedder in embedders.items():
        collection_name = f"{embedder_name}"
        directory_watcher.create_collection_for_embedder(collection_name, embedder)

    directory_watcher.start()

    session = SessionLocal()
    directories = session.query(Directory).all()
    for directory in directories:
        directory_watcher.add_directory(directory.path)
