from .services.image_indexing_service import ImageIndexingService

image_indexing_service = ImageIndexingService.instance()

__all__ = ["image_indexing_service"]
