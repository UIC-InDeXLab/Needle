from .embedders import EmbedderManager
from .generators import ImageGenerator
from .query import QueryManager

embedder_manager: EmbedderManager = EmbedderManager.instance()
query_manager: QueryManager = QueryManager.instance()

image_generator: ImageGenerator = ImageGenerator.instance()

# Imported after the others so it can lazily reference them.
from .setup import SetupManager

setup_manager: SetupManager = SetupManager.instance()

__all__ = ["embedder_manager", "query_manager", "image_generator", "setup_manager"]
