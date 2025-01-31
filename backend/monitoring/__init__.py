from .logger import logger

from .directory_watcher import ImageIndexingService

directory_watcher = ImageIndexingService.instance()

__all__ = ["directory_watcher", "logger"]
