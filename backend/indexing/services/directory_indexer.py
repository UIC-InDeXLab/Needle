from monitoring import logger
from sqlalchemy.orm import Session
from models.models import Directory
from indexing.repositories.repositories import MilvusRepository, ImageRepository
from indexing.services.embedder_service import EmbedderService
from settings import settings


class DirectoryIndexer:
    def __init__(self, embedder_service: EmbedderService, milvus_repo: MilvusRepository):
        self.embedder_service = embedder_service
        self.milvus_repo = milvus_repo

    def index_directory(self, directory_id: int, directory_path: str, session: Session):
        logger.info(f"Starting indexing for directory {directory_path} (ID: {directory_id})")
        image_repo = ImageRepository(session)
        unindexed_images = image_repo.get_unindexed_images(directory_id)
        total_images = len(unindexed_images)
        if total_images == 0:
            logger.info(f"No images to index in directory {directory_path}")
            return

        batch_size = settings.directory.batch_size
        for i in range(0, total_images, batch_size):
            batch = unindexed_images[i:i + batch_size]
            batch_paths = [img.path for img in batch]
            logger.debug(f"Processing batch {i // batch_size + 1} with {len(batch)} images")

            # Compute embeddings for the current batch in one forward pass per embedder
            embeddings = self.embedder_service.compute_batch_embeddings(batch_paths)

            # Accumulate Milvus entries for each embedder in this batch
            embedder_batches = {}
            for img in batch:
                if img.path in embeddings:
                    for embedder_name, emb in embeddings[img.path].items():
                        embedder_batches.setdefault(embedder_name, []).append({
                            "directory_id": directory_id,
                            "image_path": img.path,
                            "embedding": emb
                        })
                    # Mark the image as indexed in the DB
                    img.is_indexed = True

            # Insert all embeddings for each embedder in one batch call
            for embedder_name, entries in embedder_batches.items():
                self.milvus_repo.insert_entries(embedder_name, entries)

            session.commit()

        # Mark the directory as fully indexed
        directory = session.query(Directory).get(directory_id)
        directory.is_indexed = True
        session.commit()
        logger.info(f"Completed indexing for directory {directory_path}")
