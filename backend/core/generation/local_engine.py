"""On-device text-to-image generation.

Runs diffusion models locally through diffusers, preferring the Apple Silicon
GPU (MPS) or CUDA when the user has opted into GPU acceleration. The catalog is
deliberately biased towards *distilled* models (SD-Turbo, SDXL-Turbo) which
produce an image in 1-4 denoising steps instead of the usual 25-50, because
speed is the priority for search-time generation.

Weights are not bundled: the first use of a model downloads it from the Hugging
Face hub with byte-level progress so the UI can show a real progress bar.
"""

import io
import threading
import time
from typing import Dict, List, Optional

from PIL import Image

from core.download_progress import format_eta, track_downloads
from core.generation.base import GenerationEngine, resolve_size
from monitoring import logger

# Only distilled, few-step models are listed: they render an image in 1-4
# denoising steps instead of the usual 25-50, which is what makes local
# generation practical. ``download_mb`` is the measured size of the fp16
# variant, which is what we request -- the full-precision weights are ~2x
# larger and we would only cast them down on load anyway.
MODELS: Dict[str, Dict] = {
    "sd-turbo": {
        "repo": "stabilityai/sd-turbo",
        "label": "SD-Turbo",
        "description": "Fastest. One step, about 0.6s per image. The best default.",
        "default_steps": 1,
        "max_steps": 4,
        "guidance": 0.0,
        "default_size": 512,
        "sizes": [384, 512],
        "dtype": "float16",
        "variant": "fp16",
        "download_mb": 2580,
        "tier": "fast",
        "slice_vae": False,
    },
    "sdxl-turbo": {
        "repo": "stabilityai/sdxl-turbo",
        "label": "SDXL-Turbo",
        "description": "Noticeably more detail, still only 1-4 steps. Larger download.",
        "default_steps": 2,
        "max_steps": 8,
        "guidance": 0.0,
        "default_size": 512,
        "sizes": [512, 768, 1024],
        "dtype": "float16",
        "variant": "fp16",
        "download_mb": 6938,
        "tier": "quality",
        "slice_vae": True,
    },
}

DEFAULT_MODEL = "sd-turbo"

# A loaded pipeline holds several GB. On Apple Silicon that memory is shared with
# the search embedders and everything else on the machine, and going into swap
# costs far more than reloading from the local cache (seconds vs. a ~40x
# slowdown from thrashing). So drop it once generation has been idle a while.
IDLE_UNLOAD_SECONDS = 300


def _torch():
    import torch

    return torch


class LocalDiffusionEngine(GenerationEngine):
    """Generates images in-process on the local GPU/CPU."""

    name = "needle-local"
    # Older configs referred to the companion service that this engine replaced.
    aliases = ["local", "needle-generator", "remote"]
    description = "Built in. Runs on this machine — no server, no API key."
    required_params = []
    requires_credentials = False

    def __init__(self):
        self._pipe = None
        self._pipe_model: Optional[str] = None
        self._lock = threading.Lock()
        self._state = {"state": "idle", "message": "", "current": 0, "total": 0, "model": None}
        # Guards `_pending`, the model a background load is currently running for.
        self._pending_lock = threading.Lock()
        self._pending: Optional[str] = None
        self._last_progress_ts = 0.0
        self._last_used = 0.0
        self._reaper: Optional[threading.Thread] = None
        self._import_error: Optional[str] = None

    # -- availability -----------------------------------------------------
    def libraries_available(self) -> bool:
        """True if this build can run on-device generation at all (the diffusion
        libraries are importable). Says nothing about downloaded weights."""
        try:
            import diffusers  # noqa: F401

            self._import_error = None
            return True
        except Exception as exc:
            # Packaged builds can miss a transitive dependency, which would
            # otherwise fail silently and just show "unavailable" in the UI.
            if self._import_error is None:
                self._import_error = f"{type(exc).__name__}: {exc}"
                logger.error(f"On-device generation unavailable: {self._import_error}", exc_info=True)
            return False

    def has_downloaded_model(self) -> bool:
        return any(is_downloaded(m) for m in MODELS)

    def is_available(self) -> bool:
        """Usable for generation *right now*. Weights are several GB and are only
        fetched on request, so an engine without any downloaded model is not
        available -- otherwise search would silently trigger a huge download."""
        return self.libraries_available() and self.has_downloaded_model()

    def import_error(self) -> Optional[str]:
        return self._import_error

    def device(self) -> str:
        from core.device import select_device

        return str(select_device())

    # -- progress ---------------------------------------------------------
    def _set_state(self, state, message="", current=0, total=0, model=None):
        self._state = {
            "state": state,
            "message": message,
            "current": current,
            "total": total,
            "model": model or self._pipe_model,
        }

    def _report_download(self, downloaded, total, rate):
        now = time.time()
        if downloaded < total and (now - self._last_progress_ts) < 0.2:
            return
        self._last_progress_ts = now
        label = MODELS.get(self._state.get("model") or "", {}).get("label", "model")
        if downloaded >= total:
            msg = f"Loading {label} into memory…"
        else:
            pct = int(downloaded * 100 / total) if total else 0
            eta = (total - downloaded) / rate if rate and rate > 0 else None
            msg = (
                f"Downloading {label}: {pct}% "
                f"({downloaded / 1e6:.0f}/{total / 1e6:.0f} MB, ETA {format_eta(eta)})"
            )
        self._state = {
            "state": "downloading",
            "message": msg,
            "current": int(downloaded),
            "total": int(total),
            "model": self._state.get("model"),
        }

    def state(self) -> Dict:
        return dict(self._state, loaded_model=self._pipe_model, device=self.device())

    # -- pipeline ---------------------------------------------------------
    def _dtype(self, pref: str, device: str):
        torch = _torch()
        if device == "cpu":
            # float16 on CPU is emulated and far slower than float32.
            return torch.float32
        if pref == "bfloat16":
            return torch.bfloat16
        return torch.float16

    def _load(self, model_id: str):
        """Load ``model_id``, replacing whatever is currently resident."""
        from diffusers import AutoPipelineForText2Image

        torch = _torch()
        spec = MODELS[model_id]
        device = self.device()
        dtype = self._dtype(spec.get("dtype", "float16"), device)

        # Only one pipeline stays resident: these models are several GB and the
        # unified memory on Apple Silicon is shared with everything else.
        if self._pipe is not None:
            self._pipe = None
            self._pipe_model = None
            self._free_memory(device)

        self._set_state("loading", f"Loading {spec['label']}…", model=model_id)
        logger.info(f"[generate] loading {spec['repo']} on {device} (dtype={dtype})")

        with track_downloads(self._report_download):
            kwargs = {"torch_dtype": dtype, "safety_checker": None, "use_safetensors": True}
            variant = spec.get("variant")
            try:
                pipe = AutoPipelineForText2Image.from_pretrained(
                    spec["repo"], variant=variant, **kwargs
                )
            except Exception as exc:
                # Not every revision ships a half-precision variant; fall back to
                # the default weights rather than failing the whole load.
                if not variant:
                    raise
                logger.warning(f"[generate] fp16 variant unavailable ({exc}); using default weights")
                pipe = AutoPipelineForText2Image.from_pretrained(spec["repo"], **kwargs)
        pipe = pipe.to(device)

        try:
            pipe.set_progress_bar_config(disable=True)
        except Exception:
            pass
        if hasattr(pipe, "safety_checker"):
            pipe.safety_checker = None

        # VAE slicing decodes a batch one latent at a time. Benchmarked on an
        # M3 Pro it *helps* single images but roughly doubles the per-image cost
        # of a batch, so only enable it for the big models where a 1024px batch
        # would otherwise risk exhausting unified memory.
        if spec.get("slice_vae"):
            try:
                pipe.vae.enable_slicing()
            except Exception:
                pass

        # NB: do not switch the UNet/VAE to ``channels_last`` here. It is a win
        # on CUDA but measured 2x slower for a single image and ~10x slower for
        # a batch on MPS.

        self._pipe = pipe
        self._pipe_model = model_id

        self._warmup(spec, device)
        self._last_used = time.time()
        self._start_reaper()
        self._set_state("ready", f"{spec['label']} ready", model=model_id)
        return pipe

    def _start_reaper(self):
        """Background thread that unloads the pipeline once it goes idle."""
        if self._reaper is not None and self._reaper.is_alive():
            return

        def reap():
            while True:
                time.sleep(30)
                if self._pipe is None:
                    return
                if time.time() - self._last_used < IDLE_UNLOAD_SECONDS:
                    continue
                logger.info("[generate] unloading idle pipeline to free memory")
                self.unload()
                return

        self._reaper = threading.Thread(target=reap, daemon=True)
        self._reaper.start()

    def _warmup(self, spec: Dict, device: str):
        """Run one throwaway image so Metal/CUDA kernels are compiled up front.

        Without this the *first* real request pays a multi-second compilation
        cost, which is very visible when generation itself takes ~1s.
        """
        if device == "cpu":
            return
        try:
            started = time.perf_counter()
            self._set_state("warming", f"Warming up {spec['label']}…", model=self._pipe_model)
            self._pipe(
                prompt="warmup",
                num_inference_steps=1,
                guidance_scale=0.0,
                width=spec["default_size"],
                height=spec["default_size"],
                num_images_per_prompt=1,
            )
            logger.info(f"[generate] warmup took {time.perf_counter() - started:.1f}s")
        except Exception as exc:
            logger.warning(f"[generate] warmup skipped: {exc}")

    @staticmethod
    def _free_memory(device: str):
        torch = _torch()
        try:
            if device == "cuda":
                torch.cuda.empty_cache()
            elif device == "mps":
                torch.mps.empty_cache()
        except Exception:
            pass

    def begin_load(self, model_id: str) -> Optional[Dict]:
        """Mark a load as starting and report whether a worker should be spawned.

        Returns ``None`` when a load/download for this model is already running,
        so repeated clicks do not queue duplicate threads that would then block
        on the pipeline lock.
        """
        model_id = model_id if model_id in MODELS else DEFAULT_MODEL
        with self._pending_lock:
            if self._pending == model_id:
                return None
            self._pending = model_id
        spec = MODELS[model_id]
        verb = "Loading" if is_downloaded(model_id) else "Preparing download of"
        self._set_state("loading", f"{verb} {spec['label']}…", model=model_id)
        return self._state

    def _end_load(self, model_id: str):
        with self._pending_lock:
            if self._pending == model_id:
                self._pending = None

    def ensure_loaded(self, model_id: str):
        model_id = model_id if model_id in MODELS else DEFAULT_MODEL
        if self._pipe is not None and self._pipe_model == model_id:
            self._end_load(model_id)
            return self._pipe
        with self._lock:
            if self._pipe is not None and self._pipe_model == model_id:
                return self._pipe
            try:
                return self._load(model_id)
            except Exception as exc:
                self._set_state("error", str(exc), model=model_id)
                raise
            finally:
                self._end_load(model_id)

    def unload(self):
        with self._lock:
            device = self.device()
            self._pipe = None
            self._pipe_model = None
            self._free_memory(device)
            self._set_state("idle", "")

    # -- generation -------------------------------------------------------
    def generate(
        self,
        prompt: str,
        num_images: int,
        image_size,
        params: Dict,
    ) -> List[Image.Image]:
        images, _ = self.generate_detailed(prompt, num_images, image_size, params)
        return images

    def generate_detailed(self, prompt: str, num_images: int, image_size, params: Dict):
        """Same as ``generate`` but also returns timing/seed metadata."""
        torch = _torch()
        params = params or {}
        model_id = params.get("model") if params.get("model") in MODELS else DEFAULT_MODEL
        spec = MODELS[model_id]

        height, width = resolve_size(image_size)
        width = int(params.get("width") or width)
        height = int(params.get("height") or height)
        steps = int(params.get("steps") or spec["default_steps"])
        steps = max(1, min(steps, spec["max_steps"]))
        num_images = max(1, int(num_images))

        pipe = self.ensure_loaded(model_id)

        seed = params.get("seed")
        generator = None
        if seed not in (None, "", -1):
            # Seeded generation stays on the CPU: the MPS generator does not
            # support manual seeding consistently across torch versions.
            seed = int(seed)
            generator = torch.Generator("cpu").manual_seed(seed)
        else:
            seed = None

        self._set_state("generating", "Generating…", model=model_id)
        started = time.perf_counter()
        result = pipe(
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=spec.get("guidance", 0.0),
            width=width,
            height=height,
            num_images_per_prompt=num_images,
            generator=generator,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self._last_used = time.time()
        self._set_state("ready", f"{spec['label']} ready", model=model_id)

        images = [im.convert("RGB") for im in result.images]
        meta = {
            "model": model_id,
            "steps": steps,
            "width": width,
            "height": height,
            "seed": seed,
            "device": self.device(),
            "elapsed_ms": elapsed_ms,
            "ms_per_image": int(elapsed_ms / max(1, len(images))),
        }
        logger.info(
            f"[generate] {len(images)} image(s) {width}x{height} "
            f"{model_id}/{steps} steps in {elapsed_ms}ms on {meta['device']}"
        )
        return images, meta

    # -- catalog ----------------------------------------------------------
    def capabilities(self, params: Dict = None) -> Dict:
        return {
            "service": "Needle (on-device)",
            "device": self.device(),
            "default_model": DEFAULT_MODEL,
            "loaded_model": self._pipe_model,
            "models": [self.model_card(m) for m in MODELS],
        }

    @staticmethod
    def model_card(model_id: str) -> Dict:
        spec = MODELS[model_id]
        return {
            "id": model_id,
            "label": spec["label"],
            "description": spec["description"],
            "default_steps": spec["default_steps"],
            "max_steps": spec["max_steps"],
            "sizes": spec["sizes"],
            "default_size": spec["default_size"],
            "download_mb": spec["download_mb"],
            "tier": spec["tier"],
            "downloaded": is_downloaded(model_id),
        }


def is_downloaded(model_id: str) -> bool:
    """True if the model's weights are already in the local Hugging Face cache."""
    try:
        from huggingface_hub import scan_cache_dir

        repo = MODELS[model_id]["repo"]
        for entry in scan_cache_dir().repos:
            if entry.repo_id == repo and entry.size_on_disk > 0:
                # A partial download leaves a much smaller footprint than the
                # finished weights, so require most of the expected size.
                return entry.size_on_disk >= MODELS[model_id]["download_mb"] * 1e6 * 0.8
    except Exception:
        pass
    return False


def to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
