import json
import os
from typing import Dict

from .singleton import Singleton


@Singleton
class Configuration:
    def __init__(self):
        with open(os.getenv("CONFIG_PATH"), "r+") as f:
            self._config = json.load(f)

    @property
    def resources_dir(self):
        return self._config["resources"]

    @property
    def embedders(self):
        return self._config["embedders"]

    def get_embedder_details(self, name: str) -> Dict:
        return [e for e in self._config["embedders"] if str(e["name"]).strip().lower() == name.strip().lower()].pop()

    @property
    def tiles_path(self):
        return self._config["tiles_path"]