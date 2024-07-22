import os
import pickle
from typing import List

from models import Configuration
from models.image import ImageFile
from models.singleton import Singleton


class Tile:
    def __init__(self, binary_png, parent: ImageFile, image_index: int):
        self._image_index = image_index
        self._parent = parent
        self._bin = binary_png
        self._vector_index = None

    @property
    def vector_index(self):
        return self._vector_index

    @vector_index.setter
    def vector_index(self, index: int):
        self._vector_index = index

    @property
    def parent(self):
        return self._parent

    @property
    def image_index(self):
        return self._image_index

    @property
    def bin(self):
        return self._bin

    def clean_binary(self):
        self._bin = None


@Singleton
class TileManager:
    def __init__(self):
        self._tiles = self.load()

    @property
    def path(self):
        return Configuration.instance().tiles_path

    def add_tile(self, tile: Tile):
        self._tiles.append(tile)

    def save(self):
        with open(self.path, "wb") as f:
            pickle.dump(self._tiles, f)

    def load(self) -> List[Tile]:
        if os.path.exists(self.path):
            with open(self.path, "rb") as f:
                return pickle.load(f)
        return []
