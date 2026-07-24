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
        indexed_any = False
        for i in range(0, total_images, batch_size):
            batch = unindexed_images[i:i + batch_size]
            batch_paths = [img.path for img in batch]
            logger.debug(f"Processing batch {i // batch_size + 1} with {len(batch)} images")

            # Compute embeddings for the current batch in one forward pass per embedder
            embeddings = self.embedder_service.compute_batch_embeddings(batch_paths)

            # Accumulate Milvus entries for each embedder in this batch
            embedder_batches = {}
            for img in batch:
                # Only accept images for which at least one embedder produced a
                # usable embedding. Without this guard an image could be marked
                # indexed while no vector is stored (e.g. if embedders were not
                # yet loaded), silently breaking search.
                img_embeddings = embeddings.get(img.path) or {}
                usable = {n: e for n, e in img_embeddings.items() if e is not None}
                if not usable:
                    logger.warning(f"No embeddings produced for '{img.path}'; leaving it unindexed")
                    continue
                for embedder_name, emb in usable.items():
                    embedder_batches.setdefault(embedder_name, []).append({
                        "directory_id": directory_id,
                        "image_path": img.path,
                        "embedding": emb
                    })
                # Mark the image as indexed in the DB
                img.is_indexed = True
                indexed_any = True

            # Insert all embeddings for each embedder in one batch call
            for embedder_name, entries in embedder_batches.items():
                self.milvus_repo.insert_entries(embedder_name, entries)

            session.commit()

        # Mark the directory as fully indexed only if we actually stored vectors.
        if indexed_any:
            directory = session.query(Directory).get(directory_id)
            directory.is_indexed = True
            session.commit()
            logger.info(f"Completed indexing for directory {directory_path}")
        else:
            logger.error(
                f"Indexing produced no embeddings for '{directory_path}'; "
                "directory left unindexed (are the embedder models loaded?)"
            )
