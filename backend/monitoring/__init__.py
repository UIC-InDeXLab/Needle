from .logger import logger

from .directory_watcher import ImageIndexer

directory_watcher = ImageIndexer.instance()

__all__ = ["directory_watcher", "logger"]
