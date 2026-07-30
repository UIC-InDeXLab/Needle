"""Base types for text-to-image generation engines."""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from PIL import Image

# Named sizes → pixel dimensions (square).
SIZE_MAP = {"SMALL": 384, "MEDIUM": 512, "LARGE": 768}


def resolve_size(image_size) -> Tuple[int, int]:
    """Resolve a named size ("SMALL"/"MEDIUM"/"LARGE") or int to (height, width)."""
    if isinstance(image_size, int):
        return image_size, image_size
    px = SIZE_MAP.get(str(image_size).upper(), 512)
    return px, px


class GenerationEngine(ABC):
    """Interface implemented by every generation backend."""

    #: Stable identifier used in configs and API requests.
    name: str = "engine"
    #: Legacy/alternate identifiers also accepted from stored configs.
    aliases: List[str] = []
    #: Human-readable description shown in the UI.
    description: str = ""
    #: Credentials/params the user must supply, e.g. [{"name": "api_key", ...}].
    required_params: List[Dict[str, str]] = []
    #: Whether the engine needs user-provided credentials to work.
    requires_credentials: bool = False

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the engine can run right now (deps/credentials present)."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        num_images: int,
        image_size,
        params: Dict,
    ) -> List[Image.Image]:
        """Generate ``num_images`` images for ``prompt`` and return PIL images."""

    def info(self, credentials_set: bool) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "required_params": self.required_params,
            "available": self.is_available(),
            "requires_credentials": self.requires_credentials,
            "credentials_set": credentials_set,
        }
