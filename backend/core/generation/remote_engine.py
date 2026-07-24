"""Remote generator engine.

Connects to a user-run generator service over HTTP (IP/port/endpoint) instead of
bundling a diffusion model. This keeps the desktop app lightweight — the heavy,
GPU-hungry generation runs wherever the user chooses.

Expected service contract (see the standalone ``generator-service``):
    POST {base_url}{generate_path}   (default generate_path = /generate)
      body: {"prompt": str, "num_images": int, "image_size": str,
             "width": int, "height": int}
      response (any of):
        {"images": ["<base64>", ...]}
        {"images": [{"base64_image": "<base64>", "engine_name": "..."}, ...]}
"""

import base64
from io import BytesIO
from typing import Dict, List

import requests
from PIL import Image

from monitoring import logger

from .base import GenerationEngine, resolve_size
from .credentials import credentials_set, get_credential


def _decode_any(value) -> Image.Image:
    if value.startswith("data:"):
        value = value.split(",", 1)[1]
    return Image.open(BytesIO(base64.b64decode(value))).convert("RGB")


class RemoteGeneratorEngine(GenerationEngine):
    name = "needle-generator"
    #: Legacy identifiers still accepted from stored configs / search requests.
    aliases = ["remote"]
    description = (
        "The Needle Generator companion app. Run it on any machine (GPU or CPU), "
        "connect it here, and switch between its image models per search. "
        "Optional — no model ships inside Needle itself."
    )
    required_params = [
        {"name": "base_url", "description": "Base URL, e.g. http://127.0.0.1:8001"},
    ]
    requires_credentials = True

    def _cfg(self, params: Dict, key: str, default=None):
        return params.get(key) or get_credential(self.name, key) or default

    def is_available(self) -> bool:
        return credentials_set(self.name, ["base_url"])

    def _base_url(self, params: Dict) -> str:
        base_url = self._cfg(params, "base_url")
        if not base_url:
            raise RuntimeError("Needle Generator URL is not configured")
        return base_url.rstrip("/")

    def capabilities(self, params: Dict = None) -> Dict:
        """Fetch the connected service's advertised models/limits (or {} if down)."""
        params = params or {}
        try:
            base_url = self._base_url(params)
        except RuntimeError:
            return {}
        try:
            resp = requests.get(base_url + "/capabilities", timeout=8)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # service not running / unreachable
            logger.info(f"Needle Generator capabilities unavailable at {base_url}: {exc}")
            return {}

    def generate(
        self, prompt: str, num_images: int, image_size, params: Dict
    ) -> List[Image.Image]:
        base_url = self._base_url(params)
        path = self._cfg(params, "generate_path", "/generate")
        url = base_url + "/" + str(path).lstrip("/")
        height, width = resolve_size(image_size)
        payload = {
            "prompt": prompt,
            "num_images": max(1, int(num_images)),
            "image_size": image_size,
            "width": width,
            "height": height,
        }
        model = self._cfg(params, "model")
        if model:
            payload["model"] = model
        logger.info(
            f"Requesting {payload['num_images']} image(s) from Needle Generator at {url}"
            + (f" (model={model})" if model else "")
        )
        resp = requests.post(url, json=payload, timeout=600)
        resp.raise_for_status()
        return self._parse(resp.json())

    @staticmethod
    def _parse(data) -> List[Image.Image]:
        items = data.get("images", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise RuntimeError("Unexpected response from generator service")
        images: List[Image.Image] = []
        for item in items:
            if isinstance(item, dict):
                b64 = item.get("base64_image") or item.get("b64_json") or item.get("image")
            else:
                b64 = item
            if b64:
                images.append(_decode_any(b64))
        if not images:
            raise RuntimeError("Generator service returned no images")
        return images
