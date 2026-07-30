import threading
import time
from monitoring import logger

from watchdog.observers import Observer

from core.singleton import Singleton
from indexing.watchers.image_change_handler import ImageChangeHandler


@Singleton
class FileWatcherService:
    def __init__(self):
        self.observer = Observer()
        self.handlers = {}

    def add_directory(self, directory_id: int, directory_path: str):
        # Re-watching the same path would stack duplicate handlers, and every
        # event would then be applied twice.
        self.remove_directory(directory_path)
        handler = ImageChangeHandler(directory_id, directory_path)
        watch = self.observer.schedule(handler, directory_path, recursive=True)
        self.handlers[directory_path] = (handler, watch)
        logger.info(f"Started filesystem watcher for {directory_path}")

    def remove_directory(self, directory_path: str):
        if directory_path in self.handlers:
            handler, watch = self.handlers.pop(directory_path)
            try:
                self.observer.unschedule(watch)
            except Exception as exc:
                logger.warning(f"Could not unschedule watcher for {directory_path}: {exc}")
            # Flush whatever the handler had buffered so a rename or deletion
            # right before removal is not silently dropped.
            handler.stop()
            logger.info(f"Stopped filesystem watcher for {directory_path}")

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()
