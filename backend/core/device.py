"""Runtime device selection shared by embedders and the local generator.

Respects the user's onboarding GPU choice: GPU is only used when the user opted
in AND the installed torch build can actually use it.
"""

import platform

import torch

from monitoring import logger


def cuda_available() -> bool:
    try:
        return torch.cuda.is_available()
    except Exception:
        return False


def mps_available() -> bool:
    try:
        return torch.backends.mps.is_available() and platform.system() == "Darwin"
    except Exception:
        return False


def gpu_available() -> bool:
    """True if any GPU backend usable by the current torch build is present."""
    return cuda_available() or mps_available()


def select_device() -> torch.device:
    from core import setup_manager

    use_gpu = setup_manager.use_gpu()
    if use_gpu and cuda_available():
        return torch.device("cuda")
    if use_gpu and mps_available():
        return torch.device("mps")
    return torch.device("cpu")
