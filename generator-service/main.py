"""Needle Generator Service — the optional text-to-image companion for Needle.

Part of the Needle suite. Run this wherever you have a GPU (or CPU). The Needle
desktop app connects to it via the "Needle Generator" engine by pointing at this
service's URL, then discovers the models it offers through ``/capabilities`` and
lets you switch between them per search.

API:
    GET  /health          -> {status, service, device, model}
    GET  /capabilities    -> {service, version, device, default_model, models: [...]}
    GET  /engines         -> [{name, description, required_params}]  (back-compat)
    POST /generate        -> {"images": [{"base64_image": "...", "engine_name": "..."}]}
        body: {"prompt": str, "num_images": int, "model": str,
               "width": int, "height": int, "image_size": str, "steps": int?}

Environment:
    GEN_MODELS   Comma-separated subset of model ids to expose (default: all).
    GEN_MODEL    Default model id (default: sd-turbo).
    GEN_HOST     Bind host (default: 0.0.0.0)
    GEN_PORT     Bind port (default: 8001)
"""

import base64
import io
import os
import platform
import threading
from typing import Dict, List, Optional

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Model catalog. Each entry describes a diffusers text-to-image model plus the
# defaults the Needle UI should use. ``default_steps``/``guidance`` are tuned for
# each model family so a single "num_images"/"size" request just works.
# ---------------------------------------------------------------------------
MODELS: Dict[str, Dict] = {
    "sd-turbo": {
        "repo": "stabilityai/sd-turbo",
        "label": "SD-Turbo",
        "description": "Fastest. Single-step generation, great for quick previews.",
        "default_steps": 1,
        "guidance": 0.0,
        "default_size": 512,
        "sizes": [384, 512],
        "dtype": "float16",
    },
    "sdxl-turbo": {
        "repo": "stabilityai/sdxl-turbo",
        "label": "SDXL-Turbo",
        "description": "Higher quality at 512-1024px, still very fast (1-4 steps).",
        "default_steps": 2,
        "guidance": 0.0,
        "default_size": 512,
        "sizes": [512, 768, 1024],
        "dtype": "float16",
    },
    "flux-schnell": {
        "repo": "black-forest-labs/FLUX.1-schnell",
        "label": "FLUX.1-schnell",
        "description": "Best quality. Large model; needs a capable GPU. ~4 steps.",
        "default_steps": 4,
        "guidance": 0.0,
        "default_size": 1024,
        "sizes": [512, 768, 1024],
        "dtype": "bfloat16",
    },
}

# Which models this instance exposes (subset via GEN_MODELS), preserving order.
_requested = [m.strip() for m in os.environ.get("GEN_MODELS", "").split(",") if m.strip()]
ENABLED_MODELS = [m for m in _requested if m in MODELS] or list(MODELS.keys())

DEFAULT_MODEL = os.environ.get("GEN_MODEL", "sd-turbo")
if DEFAULT_MODEL not in ENABLED_MODELS:
    DEFAULT_MODEL = ENABLED_MODELS[0]

app = FastAPI(title="Needle Generator Service", version=VERSION)

# Only one model stays resident at a time to bound (V)RAM. Switching models
# unloads the previous pipeline.
_pipe = None
_pipe_model: Optional[str] = None
_lock = threading.Lock()


def _device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available() and platform.system() == "Darwin":
        return "mps"
    return "cpu"


def _resolve_dtype(pref: str, device: str):
    if device == "cpu":
        return torch.float32
    if pref == "bfloat16":
        return torch.bfloat16
    return torch.float16


def _get_pipe(model_id: str):
    """Return the pipeline for ``model_id``, loading (and swapping) as needed."""
    global _pipe, _pipe_model
    if _pipe is not None and _pipe_model == model_id:
        return _pipe
    with _lock:
        if _pipe is not None and _pipe_model == model_id:
            return _pipe
        from diffusers import AutoPipelineForText2Image

        spec = MODELS[model_id]
        device = _device()
        dtype = _resolve_dtype(spec.get("dtype", "float16"), device)

        # Free the previously loaded model before loading a new one.
        if _pipe is not None:
            del _pipe
            _pipe = None
            _pipe_model = None
            if device == "cuda":
                torch.cuda.empty_cache()

        print(
            f"[generator] loading {spec['repo']} ({model_id}) on {device} "
            f"(dtype={dtype}) - first run downloads weights"
        )
        pipe = AutoPipelineForText2Image.from_pretrained(spec["repo"], torch_dtype=dtype)
        pipe = pipe.to(device)
        try:
            pipe.set_progress_bar_config(disable=True)
        except Exception:
            pass
        if hasattr(pipe, "safety_checker"):
            pipe.safety_checker = None
        _pipe = pipe
        _pipe_model = model_id
        return _pipe


class GenerateRequest(BaseModel):
    prompt: str
    num_images: int = 1
    model: Optional[str] = None
    image_size: Optional[str] = "MEDIUM"
    width: Optional[int] = None
    height: Optional[int] = None
    steps: Optional[int] = None


def _b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _model_card(model_id: str) -> Dict:
    spec = MODELS[model_id]
    return {
        "id": model_id,
        "label": spec["label"],
        "description": spec["description"],
        "default_steps": spec["default_steps"],
        "sizes": spec["sizes"],
        "default_size": spec["default_size"],
    }


@app.get("/health")
def health():
    return {
        "status": "running",
        "service": "Needle Generator",
        "device": _device(),
        "model": _pipe_model or DEFAULT_MODEL,
    }


@app.get("/capabilities")
def capabilities():
    return {
        "service": "Needle Generator",
        "version": VERSION,
        "device": _device(),
        "default_model": DEFAULT_MODEL,
        "loaded_model": _pipe_model,
        "models": [_model_card(m) for m in ENABLED_MODELS],
    }


@app.get("/engines")
def engines():
    # Back-compat: expose each model as an "engine".
    return [
        {"name": m, "description": MODELS[m]["description"], "required_params": []}
        for m in ENABLED_MODELS
    ]


@app.post("/generate")
def generate(req: GenerateRequest):
    model_id = req.model if req.model in MODELS else DEFAULT_MODEL
    if model_id not in ENABLED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model '{model_id}' is not enabled")
    spec = MODELS[model_id]

    default_px = spec["default_size"]
    width = int(req.width or default_px)
    height = int(req.height or default_px)
    steps = int(req.steps) if req.steps else spec["default_steps"]

    pipe = _get_pipe(model_id)
    result = pipe(
        prompt=req.prompt,
        num_inference_steps=max(1, steps),
        guidance_scale=spec.get("guidance", 0.0),
        width=width,
        height=height,
        num_images_per_prompt=max(1, int(req.num_images)),
    )
    images: List[Image.Image] = list(result.images)
    return {"images": [{"base64_image": _b64(im), "engine_name": model_id} for im in images]}


if __name__ == "__main__":
    host = os.environ.get("GEN_HOST", "0.0.0.0")
    port = int(os.environ.get("GEN_PORT", "8001"))
    print(f"[generator] Needle Generator v{VERSION} - models: {', '.join(ENABLED_MODELS)}")
    uvicorn.run(app, host=host, port=port)
