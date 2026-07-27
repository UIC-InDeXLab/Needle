"""Byte-level progress reporting for huggingface_hub downloads.

huggingface_hub renders download progress through tqdm. In the packaged app the
backend runs as a subprocess without a TTY, so tqdm is *disabled*: it renders
nothing and ``update()`` is a no-op. We therefore subclass it and count bytes
ourselves, which works in both cases, and never render anything.

Both transports are covered:

* the classic HTTP path, which drives a single tqdm bar, and
* the Xet path, whose ``XetDownloadProgressReporter`` drives two bars -- one for
  bytes reconstructed to disk (with a real total) and one for raw network bytes
  (whose total is a moving estimate). Only the former is tracked, otherwise the
  same download would be counted twice.

Usage::

    with track_downloads(lambda done, total, rate: ...):
        model.download()
"""

import importlib
import sys
import time
from contextlib import contextmanager

# Downloads smaller than this are metadata (config.json, tokenizer, ...) rather
# than weights; reporting them would make a progress bar flicker 0->100%.
MIN_TRACKED_BYTES = 5 * 1024 * 1024

# Modules that did ``from .tqdm import tqdm`` captured the class by reference at
# import time, so they need rebinding too. ``_xet_progress_reporting`` is only
# imported lazily from inside ``xet_get``, so these are imported explicitly
# rather than being picked up opportunistically from sys.modules.
_CONSUMER_MODULES = (
    "huggingface_hub.file_download",
    "huggingface_hub._snapshot_download",
    "huggingface_hub.utils._xet_progress_reporting",
)


def _make_tracking_tqdm(base, callback):
    class _TrackingTqdm(base):
        def __init__(self, *args, **kwargs):
            # When tqdm is disabled, ``__init__`` returns early and never assigns
            # ``self.unit``/``self.total``, so capture them from the kwargs.
            self._needle_seen = 0
            self._needle_started = time.time()
            self._needle_total = kwargs.get("total") or 0
            bar_format = kwargs.get("bar_format") or ""
            # Xet's raw-transfer bar deliberately omits a denominator (its total
            # is inflated as bytes arrive), so it has no ``total_fmt`` field.
            # Skip it and follow the reconstruction bar, which counts real file
            # bytes -- tracking both would double-count the same download.
            self._needle_track = kwargs.get("unit", "") == "B" and (
                "total_fmt" in bar_format if bar_format else True
            )
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            try:
                if self._needle_track and isinstance(n, (int, float)) and n > 0:
                    self._needle_seen += n
                    # ``total`` gets revised upwards mid-download on the Xet
                    # path, so prefer whichever value is currently largest.
                    total = max(self._needle_total, getattr(self, "total", 0) or 0)
                    if total >= MIN_TRACKED_BYTES:
                        elapsed = time.time() - self._needle_started
                        rate = self._needle_seen / elapsed if elapsed > 0 else None
                        callback(min(self._needle_seen, total), total, rate)
            except Exception:
                pass
            return super().update(n)

    return _TrackingTqdm


@contextmanager
def track_downloads(callback):
    """Report ``callback(downloaded_bytes, total_bytes, bytes_per_second)``.

    Never raises: if huggingface_hub's internals change shape, downloads still
    run, just without progress.
    """
    try:
        importlib.import_module("huggingface_hub.utils.tqdm")
        # ``huggingface_hub.utils`` re-exports the tqdm *class*, which shadows the
        # submodule attribute, so fetch the real module from sys.modules.
        tqdm_module = sys.modules["huggingface_hub.utils.tqdm"]
        original = tqdm_module.tqdm
        if not isinstance(original, type):
            raise TypeError("unexpected huggingface_hub tqdm export")
    except Exception:
        yield
        return

    tracking = _make_tracking_tqdm(original, callback)
    tqdm_module.tqdm = tracking
    patched = [(tqdm_module, original)]
    for name in _CONSUMER_MODULES:
        try:
            consumer = importlib.import_module(name)
        except Exception:
            continue
        if getattr(consumer, "tqdm", None) is original:
            consumer.tqdm = tracking
            patched.append((consumer, original))

    try:
        yield
    finally:
        for module, restore in patched:
            module.tqdm = restore


def format_eta(seconds) -> str:
    if seconds is None or seconds < 0:
        return "?"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"
