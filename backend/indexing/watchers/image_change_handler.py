"""Filesystem watcher callbacks for a single indexed directory.

Watchdog delivers one event per file operation, and bulk operations (copying a
folder in, deleting a selection, an editor rewriting a file) produce bursts of
them. Rather than doing database and vector work per event, changes are
coalesced into a short window and applied in batches.
"""

import threading
from typing import Optional, Set

from watchdog.events import FileSystemEventHandler

from indexing.file_types import is_image
from indexing.queue_manager.index_queue_manager import IndexQueueManager
from indexing.repositories.repositories import ImageRepository, VectorRepository
from models.models import SessionLocal
from monitoring import logger

#: How long to wait for a burst of events to settle before applying them. Also
#: covers the window where a file is still being written: watchdog reports
#: `created` as soon as the entry appears, long before the bytes have landed.
FLUSH_DELAY_SECONDS = 2.0


class ImageChangeHandler(FileSystemEventHandler):
    """Collects filesystem events and applies them in coalesced batches."""

    def __init__(self, directory_id: int, directory_path: str):
        super().__init__()
        self.directory_id = directory_id
        self.directory_path = directory_path

        self._lock = threading.Lock()
        self._added: Set[str] = set()
        self._removed: Set[str] = set()
        self._changed: Set[str] = set()
        self._timer: Optional[threading.Timer] = None
        logger.debug(f"Created ImageChangeHandler for directory {directory_path} (ID: {directory_id})")

    # -- event plumbing ---------------------------------------------------
    def _schedule_flush(self):
        """(Re)start the debounce timer; callers must hold the lock."""
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(FLUSH_DELAY_SECONDS, self._flush)
        self._timer.daemon = True
        self._timer.start()

    def _record(self, added=(), removed=(), changed=()):
        with self._lock:
            for path in added:
                self._removed.discard(path)
                self._added.add(path)
            for path in removed:
                # A file removed after being added in the same window never
                # needs to be indexed at all.
                self._added.discard(path)
                self._changed.discard(path)
                self._removed.add(path)
            for path in changed:
                if path not in self._added:
                    self._changed.add(path)
            self._schedule_flush()

    def on_created(self, event):
        if not event.is_directory and is_image(event.src_path):
            self._record(added=[event.src_path])

    def on_deleted(self, event):
        if not event.is_directory and is_image(event.src_path):
            self._record(removed=[event.src_path])

    def on_modified(self, event):
        if not event.is_directory and is_image(event.src_path):
            self._record(changed=[event.src_path])

    def on_moved(self, event):
        if event.is_directory:
            return
        # Treated as a delete plus an add: the content is unchanged, but results
        # are keyed by path, so the rows for the old path have to go regardless.
        removed = [event.src_path] if is_image(event.src_path) else []
        added = [event.dest_path] if is_image(event.dest_path) else []
        if removed or added:
            self._record(added=added, removed=removed)

    def stop(self):
        """Apply anything still pending (used when the watcher is torn down)."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        self._flush()

    # -- batch application ------------------------------------------------
    def _drain(self):
        with self._lock:
            self._timer = None
            added, removed, changed = self._added, self._removed, self._changed
            self._added, self._removed, self._changed = set(), set(), set()
        return added, removed, changed

    def _flush(self):
        added, removed, changed = self._drain()
        if not (added or removed or changed):
            return

        session = SessionLocal()
        try:
            images = ImageRepository(session)
            vectors = VectorRepository()

            # Deleted and moved-away files: drop their vectors, then their rows.
            if removed:
                vectors.delete_paths_all_embedders(list(removed))
                deleted = images.delete_by_paths(list(removed))
                if deleted:
                    logger.info(f"Removed {deleted} deleted image(s) from {self.directory_path}")

            # Modified files keep their row but need re-embedding, so the stale
            # vectors must go or the index would hold both versions.
            modified = [p for p in changed if p not in added]
            if modified:
                vectors.delete_paths_all_embedders(modified)
                images.mark_unindexed(modified)

            if added:
                count = images.add_new_images(self.directory_id, sorted(added))
                if count:
                    logger.info(f"Detected {count} new image(s) in {self.directory_path}")

            if added or modified:
                IndexQueueManager.instance().add_to_queue(
                    self.directory_id, self.directory_path, priority=0
                )
        except Exception as exc:
            logger.error(f"Error applying changes in {self.directory_path}: {exc}", exc_info=True)
            session.rollback()
        finally:
            session.close()
