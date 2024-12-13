from .embedders import EmbedderManager
from .generators import ImageGenerator
from .query import QueryManager

embedder_manager: EmbedderManager = EmbedderManager.instance()
query_manager: QueryManager = QueryManager.instance()

image_generator: ImageGenerator = ImageGenerator.instance()

__all__ = ["embedder_manager", "query_manager", "image_generator"]
