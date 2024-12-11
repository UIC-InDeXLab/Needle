from .embedders import EmbedderManager
from .generators import EngineManager
from .query import QueryManager

embedder_manager: EmbedderManager = EmbedderManager.instance()
query_manager: QueryManager = QueryManager.instance()
engine_manager: EngineManager = EngineManager.instance()

__all__ = ["embedder_manager", "query_manager", "engine_manager"]
