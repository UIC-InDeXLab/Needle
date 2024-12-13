from abc import ABC
from itertools import chain

from core.connectors import ImageGeneratorConnector
from core.singleton import Singleton
from settings import settings
from utils import decode_base64_image


@Singleton
class ImageGenerator(ABC):
    def __init__(self):
        self._connector = ImageGeneratorConnector(settings.generators.url)

    def get_available_engines(self):
        return self._connector.list_engines()

    def generate(self, prompt, engine_names, k, image_size):
        engines_config = {}
        for name in engine_names:
            engines_config[name] = {"k": k, "image_size": f"{image_size}x{image_size}"}

        response = self._connector.generate_images(prompt=prompt, engines=engines_config)
        encoded_images = []
        encoded_images.extend(r["images"] for r in response.values())
        encoded_images = list(chain.from_iterable(encoded_images))
        return [decode_base64_image(img) for img in encoded_images]
