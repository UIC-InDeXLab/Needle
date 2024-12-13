from .logger import logger

from .directory_watcher import DirectoryWatcher

directory_watcher = DirectoryWatcher.instance()

__all__ = ["directory_watcher", "logger"]
