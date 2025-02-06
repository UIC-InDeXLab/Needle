import threading
import time
from monitoring import logger

from typing import Dict

from watchdog.observers import Observer

from core.singleton import Singleton
from indexing.watchers.image_change_handler import ImageChangeHandler


@Singleton
class FileWatcherService:
    def __init__(self):
        self.observer = Observer()
        self.handlers = {}

    def add_directory(self, directory_id: int, directory_path: str, embedders: Dict):
        handler = ImageChangeHandler(directory_id, directory_path, embedders)
        watch = self.observer.schedule(handler, directory_path, recursive=True)
        self.handlers[directory_path] = (handler, watch)
        logger.info(f"Started filesystem watcher for {directory_path}")

    def remove_directory(self, directory_path: str):
        if directory_path in self.handlers:
            handler, watch = self.handlers[directory_path]
            self.observer.unschedule(watch)
            del self.handlers[directory_path]
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
