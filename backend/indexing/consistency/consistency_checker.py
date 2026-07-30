import os
import threading
import time

from sqlalchemy.orm import Session

from models.models import SessionLocal, Directory
from indexing.file_types import scan_image_paths
from indexing.queue_manager.index_queue_manager import IndexQueueManager
from indexing.repositories.repositories import DirectoryRepository, ImageRepository, VectorRepository
from monitoring import logger


class ConsistencyChecker:
    def __init__(self, interval: int = 3600):
        self.interval = interval
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        while True:
            time.sleep(self.interval)
            self.check_consistency()

    def check_consistency(self):
        logger.debug("Running system-wide consistency check")
        session = SessionLocal()
        try:
            directory_repo = DirectoryRepository(session)
            # Snapshot the ids first: check_directory commits (and may delete a
            # directory), which expires the ORM objects and would make the loop
            # re-fetch each one from the database.
            directory_ids = [d.id for d in directory_repo.get_all()]
            for directory_id in directory_ids:
                directory = session.get(Directory, directory_id)
                if directory is None:
                    continue
                try:
                    self.check_directory(session, directory)
                except Exception as exc:
                    # One bad directory (permissions, unmounted drive) must not
                    # stop the others from being checked.
                    logger.error(f"Consistency check failed for directory {directory_id}: {exc}", exc_info=True)
                    session.rollback()
            logger.debug("Consistency check completed")
        except Exception as e:
            logger.error(f"Consistency check error: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def check_directory(self, session: Session, directory: Directory):
        logger.debug(f"Checking consistency for directory {directory.path} (ID: {directory.id})")
        if not os.path.exists(directory.path):
            logger.warning(f"Directory missing: {directory.path}. Removing from system.")
            # Also clears the directory's images and vectors, which used to be
            # left behind pointing at a path that no longer exists.
            DirectoryRepository(session).delete(directory)
            return

        fs_paths = scan_image_paths(directory.path)
        image_repo = ImageRepository(session)
        db_paths = image_repo.get_paths(directory.id)

        new_paths = fs_paths - db_paths
        deleted_paths = db_paths - fs_paths
        if not new_paths and not deleted_paths:
            return

        logger.info(
            f"Directory {directory.path}: {len(new_paths)} new image(s), "
            f"{len(deleted_paths)} missing image(s)"
        )

        if deleted_paths:
            # One batched delete per embedder table instead of one call per
            # path per table: removing a thousand files used to mean thousands
            # of individual table rewrites.
            VectorRepository().delete_paths_all_embedders(list(deleted_paths))
            image_repo.delete_by_paths(list(deleted_paths))

        if new_paths:
            image_repo.add_new_images(directory.id, sorted(new_paths))
            IndexQueueManager.instance().add_to_queue(directory.id, directory.path, priority=1)
