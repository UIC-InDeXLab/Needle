"""Pluggable text-to-image generation engines.

The desktop build runs generation in-process (no external service). A fast
on-device engine (SD-Turbo via ``diffusers``) is the default; API-backed engines
(OpenAI, Stability) are used when the user supplies credentials.
"""

from .base import GenerationEngine, resolve_size  # noqa: F401
