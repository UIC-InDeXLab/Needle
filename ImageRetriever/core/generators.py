from abc import ABC, abstractmethod
from typing import List

import requests

from core.connectors import SDXLTurboConnector, RunwayMLConnector, Connector, ReplicateConnector, DALLEConnector
from core.singleton import Singleton


class ImageGeneratorEngine(ABC):
    def __init__(self, connector: Connector):
        self._connector = connector
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def generate(self, prompt: str, image_size: int, k: int):
        pass


class DALLEEngine(ImageGeneratorEngine):
    def __init__(self):
        super().__init__(connector=DALLEConnector())

    @property
    def name(self):
        return "dall-e"

    def generate(self, prompt: str, image_size: int, k: int):
        res = self._connector.generate_image(prompt=prompt, size=f"{image_size}x{image_size}", n=k)
        urls = [d["url"] for d in res["data"]]
        generated_images: List[bytes] = [requests.get(url).content for url in urls]
        return generated_images


class ReplicateEngine(ImageGeneratorEngine):
    @property
    def name(self):
        return "replicate"

    def __init__(self):
        super().__init__(connector=ReplicateConnector())

    def generate(self, prompt: str, image_size: int, k: int):
        res = self._connector.generate_image(prompt=prompt, k=k)
        generated_images: List[bytes] = [requests.get(url).content for url in res["urls"]]
        return generated_images


class StableDiffusionEngine(ImageGeneratorEngine, ABC):
    def generate(self, prompt: str, image_size: int, k: int):
        generated_images: List[bytes] = [self._connector.generate_image(prompt=prompt, size=image_size) for _ in
                                         range(k)]
        return generated_images


class RunwayMLEngine(StableDiffusionEngine):
    def __init__(self):
        super().__init__(connector=RunwayMLConnector())

    @property
    def name(self):
        return "runwayml"


class SDXLTurboEngine(StableDiffusionEngine):
    def __init__(self):
        super().__init__(connector=SDXLTurboConnector())

    @property
    def name(self):
        return "sdxl-turbo"


@Singleton
class EngineManager:
    def __init__(self):
        self._supported_engines = {
            "dall-e": DALLEEngine(),
            "sdxl-turbo": SDXLTurboEngine(),
            "runwayml": RunwayMLEngine(),
            "replicate": ReplicateEngine()
        }

    @property
    def supported_engines(self):
        return list(self._supported_engines.keys())

    @property
    def default_engines(self):
        return ["runwayml"]

    def get_engine_by_name(self, name: str) -> ImageGeneratorEngine:
        return self._supported_engines[name.strip()]
