import queue
import threading
from monitoring import logger

from concurrent.futures import ThreadPoolExecutor

from core.singleton import Singleton
from models.models import SessionLocal
from indexing.repositories.repositories import MilvusRepository
from indexing.services.directory_indexer import DirectoryIndexer
from indexing.services.embedder_service import EmbedderService
from settings import settings


@Singleton
class IndexQueueManager:
    def __init__(self):
        self.index_queue = queue.PriorityQueue()
        self.processing_paths = set()
        self.queue_lock = threading.Lock()
        self.index_workers = ThreadPoolExecutor(max_workers=settings.directory.num_watcher_workers)
        self.embedder_service = EmbedderService()
        self.milvus_repo = MilvusRepository()
        self.directory_indexer = DirectoryIndexer(self.embedder_service, self.milvus_repo)

    def add_to_queue(self, directory_id: int, path: str, priority: int = 0):
        with self.queue_lock:
            if (directory_id, path) in self.processing_paths:
                # Already queued or being indexed; the running pass will pick up
                # whatever changed, so there is nothing to add.
                return
            self.index_queue.put((priority, (directory_id, path)))
            self.processing_paths.add((directory_id, path))
        logger.debug(f"Queued directory {path} (ID: {directory_id}) with priority {priority}")
        self.index_workers.submit(self._process_queue)

    def _process_queue(self):
        while True:
            try:
                # Never block: `empty()` followed by a blocking `get()` races
                # with the other workers, and the loser would park forever on an
                # empty queue, permanently consuming a thread from the pool.
                priority, (directory_id, path) = self.index_queue.get_nowait()
            except queue.Empty:
                return

            session = SessionLocal()
            try:
                self.directory_indexer.index_directory(directory_id, path, session)
            except Exception as exc:
                logger.error(f"Indexing failed for {path} (ID: {directory_id}): {exc}", exc_info=True)
                session.rollback()
            finally:
                session.close()
                with self.queue_lock:
                    self.processing_paths.discard((directory_id, path))
                self.index_queue.task_done()
                logger.debug(f"Finished processing directory {path} (ID: {directory_id})")
