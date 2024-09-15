from abc import ABC, abstractmethod
from typing import List

import requests

from models import DALLEConnector, LocalStableDiffusionConnector
from models.singleton import Singleton


class ImageGeneratorEngine(ABC):
    def __init__(self):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def generate(self, prompt: str, image_size: int, k: int):
        pass


class DALLEEngine(ImageGeneratorEngine):

    @property
    def name(self):
        return "dall-e"

    def generate(self, prompt: str, image_size: int, k: int):
        c = DALLEConnector()
        res = c.generate_image(prompt=prompt, size=f"{image_size}x{image_size}", n=k)
        urls = [d["url"] for d in res["data"]]
        generated_images: List[bytes] = [requests.get(url).content for url in urls]
        return generated_images


class StableDiffusionEngine(ImageGeneratorEngine):

    @property
    def name(self):
        return "stable-diffusion"

    def generate(self, prompt: str, image_size: int, k: int):
        c = LocalStableDiffusionConnector()
        generated_images: List[bytes] = [c.generate_image(prompt=prompt, size=image_size) for _ in range(k)]
        return generated_images


@Singleton
class EngineManager:
    def __init__(self):
        self._supported_engines = {
            "dall-e": DALLEEngine(),
            "stable-diffusion": StableDiffusionEngine()
        }

    @property
    def supported_engines(self):
        return list(self._supported_engines.keys())

    def get_engine_by_name(self, name: str) -> ImageGeneratorEngine:
        return self._supported_engines[name.strip()]
