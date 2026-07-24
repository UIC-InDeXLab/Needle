"""Entry point for the packaged desktop backend.

Runs the FastAPI app under uvicorn on a local-only port. When frozen by
PyInstaller, switches the working directory to the bundle root so the relative
``static``/``templates`` paths used by the app continue to resolve.
"""

import os
import sys

import uvicorn

# Let unsupported MPS ops fall back to CPU on Apple Silicon so image generation
# (diffusers) doesn't crash on ops not yet implemented in the Metal backend.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

# Force huggingface_hub's classic HTTP download path. The Xet backend streams
# through its own reporter and bypasses tqdm, so byte-level download progress
# would never surface on the onboarding screen. This must be set before
# huggingface_hub is imported (it is read into a module constant at import).
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

# Let CPU inference use all cores. Frozen apps / some BLAS backends otherwise
# default to a single thread, making embedding (search + indexing) very slow.
# Must be set before torch/numpy import to take effect.
_cores = os.cpu_count() or 4
os.environ.setdefault("OMP_NUM_THREADS", str(_cores))
os.environ.setdefault("MKL_NUM_THREADS", str(_cores))


def _prepare_frozen_cwd() -> None:
    # PyInstaller onefile extracts bundled data to sys._MEIPASS.
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        os.chdir(bundle_dir)
    else:
        # Running from source: ensure cwd is the backend package directory.
        os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    _prepare_frozen_cwd()

    # Ensure torch uses all CPU cores for inference (see env setup above).
    try:
        import torch

        torch.set_num_threads(_cores)
    except Exception:
        pass

    # Import after cwd is set so relative resource mounts resolve correctly.
    from main import app

    host = os.environ.get("NEEDLE_HOST", "127.0.0.1")
    port = int(os.environ.get("NEEDLE_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    main()
