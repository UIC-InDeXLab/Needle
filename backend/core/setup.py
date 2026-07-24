"""Onboarding / first-run setup manager.

Keeps first launch lightweight: no models are loaded until the user picks a
profile (fast/balanced/accurate) and a GPU option. The heavy initialization
(downloading + loading models, creating vector tables, starting indexing) runs in
a background thread with coarse progress so the UI can show a welcome flow.

State is persisted to ``<data_dir>/setup.json`` so the choice survives restarts.
"""

import json
import os
import threading
import time
from pathlib import Path

# Force huggingface_hub's classic HTTP download path so byte-level download
# progress surfaces via tqdm (the Xet backend bypasses it). Must be set before
# huggingface_hub is imported anywhere.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from core.singleton import Singleton
from monitoring import logger
from settings import settings
from settings.profiles import DEFAULT_PROFILE, get_profile, profile_options


@Singleton
class SetupManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._indexing_started = False
        self._config = self._load()
        # Runtime init progress.
        self._state = {"state": "onboarding", "message": "", "current": 0, "total": 0}
        self._current_model = ""
        self._last_progress_ts = 0.0
        if self.is_configured():
            self._state["state"] = "idle"

    # -- persistence ------------------------------------------------------
    def _setup_path(self) -> Path:
        return Path(settings.storage.data_dir, "setup.json")

    def _load(self) -> dict:
        path = self._setup_path()
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception as exc:
                logger.warning(f"Failed to read setup.json: {exc}")
        return {"configured": False, "profile": None, "use_gpu": False}

    def _save(self):
        path = self._setup_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._config, indent=2))

    # -- accessors --------------------------------------------------------
    def is_configured(self) -> bool:
        return bool(self._config.get("configured"))

    def use_gpu(self) -> bool:
        return bool(self._config.get("use_gpu"))

    def is_ready(self) -> bool:
        return self._state.get("state") == "ready"

    def _set_state(self, state, message="", current=0, total=0):
        self._state = {"state": state, "message": message, "current": current, "total": total}
        if message:
            logger.info(f"[setup] {state}: {message}")

    # -- model download progress -----------------------------------------
    @staticmethod
    def _fmt_eta(seconds):
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

    def _report_download(self, downloaded, total, rate):
        # Called very frequently by the download hook; throttle to ~5/sec and
        # update state directly (no logging) to avoid log spam.
        now = time.time()
        if downloaded < total and (now - self._last_progress_ts) < 0.2:
            return
        self._last_progress_ts = now
        pct = int(downloaded * 100 / total) if total else 0
        eta = (total - downloaded) / rate if rate and rate > 0 else None
        msg = (
            f"Downloading {self._current_model} weights: {pct}% "
            f"({downloaded / 1e6:.0f}/{total / 1e6:.0f} MB, ETA {self._fmt_eta(eta)})"
        )
        self._state = {
            "state": "downloading",
            "message": msg,
            "current": int(downloaded),
            "total": int(total),
        }

    def _install_download_hook(self):
        """Hook huggingface_hub's tqdm so weight downloads report byte-level progress."""
        import os
        import sys

        # Force the classic HTTP download path; the Xet backend streams through
        # its own reporter and bypasses tqdm, so byte-level progress would never
        # surface otherwise.
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

        try:
            import importlib

            importlib.import_module("huggingface_hub.utils.tqdm")
            # NOTE: huggingface_hub.utils re-exports the ``tqdm`` *class*, which
            # shadows the submodule attribute, so fetch the real module from
            # sys.modules rather than via attribute access.
            hf_tqdm_mod = sys.modules["huggingface_hub.utils.tqdm"]
            original = hf_tqdm_mod.tqdm
        except Exception:
            return None, None
        if not isinstance(original, type):
            return None, None
        manager = self

        class _ProgressTqdm(original):
            def __init__(self, *args, **kwargs):
                # We track bytes ourselves so progress works even when tqdm is
                # disabled (stderr not a TTY, the normal subprocess case) where
                # ``super().update`` is a no-op. We never render anything.
                self._needle_counter = 0
                self._needle_start = time.time()
                super().__init__(*args, **kwargs)

            def update(self, n=1):
                try:
                    if getattr(self, "unit", "") == "B":
                        if isinstance(n, (int, float)) and n > 0:
                            self._needle_counter += n
                        total = getattr(self, "total", None) or 0
                        elapsed = time.time() - self._needle_start
                        rate = self._needle_counter / elapsed if elapsed > 0 else None
                        if total:
                            manager._report_download(self._needle_counter, total, rate)
                except Exception:
                    pass
                return super().update(n)

        hf_tqdm_mod.tqdm = _ProgressTqdm
        # Modules that did ``from .utils import tqdm`` captured the original
        # class by reference at import time; rebind those too so the download
        # code path actually uses our subclass.
        patched = [(hf_tqdm_mod, original)]
        for name in ("huggingface_hub.file_download", "huggingface_hub._snapshot_download"):
            consumer = sys.modules.get(name)
            if consumer is not None and getattr(consumer, "tqdm", None) is original:
                consumer.tqdm = _ProgressTqdm
                patched.append((consumer, original))
        return patched, original

    @staticmethod
    def _remove_download_hook(patched, original):
        if not patched:
            return
        # ``patched`` may be a list of (module, original) pairs.
        if isinstance(patched, list):
            for module, orig in patched:
                module.tqdm = orig
        elif original is not None:
            patched.tqdm = original

    # -- public API -------------------------------------------------------
    def options(self) -> dict:
        from core.device import gpu_available

        return {
            "profiles": profile_options(),
            "default_profile": DEFAULT_PROFILE,
            "gpu_available": gpu_available(),
        }

    def status(self) -> dict:
        from core.device import gpu_available

        return {
            "configured": self.is_configured(),
            "profile": self._config.get("profile"),
            "use_gpu": self.use_gpu(),
            "gpu_available": gpu_available(),
            "state": self._state.get("state"),
            "message": self._state.get("message", ""),
            "current": self._state.get("current", 0),
            "total": self._state.get("total", 0),
            "ready": self.is_ready(),
        }

    def configure(self, profile: str, use_gpu: bool) -> dict:
        prof = get_profile(profile)  # raises ValueError on bad profile

        # Write the active embedders config into the writable data dir.
        data_dir = Path(settings.storage.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "embedders.json").write_text(
            json.dumps({"image_embedders": prof["image_embedders"]}, indent=2)
        )

        self._config = {"configured": True, "profile": profile, "use_gpu": bool(use_gpu)}
        self._save()
        self._start_init(reconfigure=True)
        return self.status()

    def startup(self):
        """Called on backend boot. Only does heavy work if already configured."""
        if self.is_configured():
            logger.info("Setup found; initializing in background.")
            self._start_init()
        else:
            logger.info("Not configured yet; waiting for onboarding.")
            self._set_state("onboarding", "Waiting for setup")

    # -- background init --------------------------------------------------
    def _start_init(self, reconfigure: bool = False):
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.info("Initialization already in progress; ignoring.")
                return
            self._set_state("loading", "Starting up", 0, 0)
            self._thread = threading.Thread(
                target=self._run_init, args=(reconfigure,), daemon=True
            )
            self._thread.start()

    def _run_init(self, reconfigure: bool):
        hook_module, hook_original = self._install_download_hook()
        try:
            from core import embedder_manager
            from core.vector_store import VectorStore
            from indexing import image_indexing_service

            # Pick up the newly-written embedders config.
            settings.reload_embedders()

            total = len(settings.image_embedders)

            def progress(i, _total, name):
                self._current_model = name
                self._set_state("loading", f"Preparing model {i + 1}/{_total}: {name}", i, _total)

            self._set_state("loading", "Loading models", 0, total)
            embedder_manager.load(progress=progress)

            self._set_state("preparing", "Preparing search index", total, total)
            vector_store = VectorStore.instance()
            for name, embedder in embedder_manager.get_image_embedders().items():
                vector_store.create_table(name, embedder.embedding_dim)

            if not self._indexing_started:
                image_indexing_service.start()
                self._indexing_started = True

            self._set_state("ready", "Ready", total, total)
        except Exception as exc:
            logger.error(f"Setup initialization failed: {exc}", exc_info=True)
            self._set_state("error", str(exc))
        finally:
            self._remove_download_hook(hook_module, hook_original)
