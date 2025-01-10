from abc import ABC

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

    def generate(self, generation_config):
        response = self._connector.generate_images(generation_config)
        return [(decode_base64_image(img["base64_image"]), img["engine_name"]) for img in response["images"]]
