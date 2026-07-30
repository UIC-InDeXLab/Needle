"""API-backed generation engines (used when the user supplies credentials)."""

import base64
from io import BytesIO
from typing import Dict, List

import requests
from PIL import Image

from monitoring import logger

from .base import GenerationEngine, resolve_size
from .credentials import credentials_set, get_credential


def _decode_b64(b64: str) -> Image.Image:
    return Image.open(BytesIO(base64.b64decode(b64))).convert("RGB")


def _download(url: str) -> Image.Image:
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGB")


class OpenAIEngine(GenerationEngine):
    name = "openai"
    description = "OpenAI image generation (DALL·E / gpt-image-1). Requires an API key."
    required_params = [{"name": "api_key", "description": "Your OpenAI API key"}]
    requires_credentials = True

    _ENDPOINT = "https://api.openai.com/v1/images/generations"

    def _api_key(self, params: Dict):
        return params.get("api_key") or get_credential(self.name, "api_key")

    def is_available(self) -> bool:
        return credentials_set(self.name, ["api_key"])

    def generate(
        self, prompt: str, num_images: int, image_size, params: Dict
    ) -> List[Image.Image]:
        api_key = self._api_key(params)
        if not api_key:
            raise RuntimeError("OpenAI API key not provided")
        model = params.get("model", "dall-e-3")
        size = params.get("size", "1024x1024")

        images: List[Image.Image] = []
        headers = {"Authorization": f"Bearer {api_key}"}
        for _ in range(max(1, int(num_images))):
            payload = {"model": model, "prompt": prompt, "n": 1, "size": size}
            # gpt-image-1 always returns b64_json and rejects response_format.
            if model != "gpt-image-1":
                payload["response_format"] = "b64_json"
            resp = requests.post(self._ENDPOINT, headers=headers, json=payload, timeout=180)
            resp.raise_for_status()
            item = resp.json()["data"][0]
            if item.get("b64_json"):
                images.append(_decode_b64(item["b64_json"]))
            elif item.get("url"):
                images.append(_download(item["url"]))
        return images


class StabilityEngine(GenerationEngine):
    name = "stability"
    description = "Stability AI (Stable Image Core). Requires an API key."
    required_params = [{"name": "api_key", "description": "Your Stability AI API key"}]
    requires_credentials = True

    _ENDPOINT = "https://api.stability.ai/v2beta/stable-image/generate/core"

    def _api_key(self, params: Dict):
        return params.get("api_key") or get_credential(self.name, "api_key")

    def is_available(self) -> bool:
        return credentials_set(self.name, ["api_key"])

    def generate(
        self, prompt: str, num_images: int, image_size, params: Dict
    ) -> List[Image.Image]:
        api_key = self._api_key(params)
        if not api_key:
            raise RuntimeError("Stability API key not provided")
        headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}

        images: List[Image.Image] = []
        for _ in range(max(1, int(num_images))):
            resp = requests.post(
                self._ENDPOINT,
                headers=headers,
                files={"none": ""},
                data={"prompt": prompt, "output_format": "png"},
                timeout=180,
            )
            resp.raise_for_status()
            images.append(Image.open(BytesIO(resp.content)).convert("RGB"))
        return images
