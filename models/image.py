import os

from PIL import Image

from models.configuration import Configuration


class ImageFile:
    def __init__(self, filename: str):
        self.filename = filename

    @property
    def path(self):
        return os.path.join(Configuration.instance().resources_dir, self.filename)

    @property
    def bin(self):
        return Image.open(self.path).convert("RGB")

