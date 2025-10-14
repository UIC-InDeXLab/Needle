from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from settings import settings


class HealthCheckResponse(BaseModel):
    status: str


class AddDirectoryRequest(BaseModel):
    path: str = Field(..., description="Path to the directory to be added")


class AddDirectoryResponse(BaseModel):
    status: str
    id: int


class ImageModel(BaseModel):
    path: str


class DirectoryModel(BaseModel):
    id: int
    path: str
    is_indexed: bool
    is_enabled: bool


class DirectoryListResponse(BaseModel):
    directories: List[DirectoryModel]


class DirectoryDetailResponse(BaseModel):
    directory: DirectoryModel
    images: List[str]
    indexing_ratio: float


class RemoveDirectoryRequest(BaseModel):
    path: str


class RemoveDirectoryResponse(BaseModel):
    status: str


class UpdateDirectoryRequest(BaseModel):
    is_enabled: bool = Field(..., description="Flag indicating if the directory is enabled for search")


class UpdateDirectoryResponse(BaseModel):
    status: str
    directory: 'DirectoryModel'


class CreateQueryRequest(BaseModel):
    q: str = Field(..., description="Query string")


class CreateQueryResponse(BaseModel):
    qid: int


class EngineConfig(BaseModel):
    name: str
    params: Dict[str, Any] = Field(..., description="Required parameters including auth")


class GenerationConfig(BaseModel):
    engines: List[EngineConfig]
    num_engines_to_use: int = Field(settings.query.num_engines_to_use, description="Number of engines to use")
    num_images: int = Field(settings.query.num_images_to_generate,
                            description="Number of images to generate per engine")
    image_size: str = Field(settings.query.generated_image_size, description="Image size in pixels")
    use_fallback: bool = Field(settings.query.use_fallback, description="Whether to use fallback engines on failure")


class SearchRequest(BaseModel):
    qid: int = Field(..., description="Query ID to search for")
    num_images_to_retrieve: int = Field(settings.query.num_images_to_retrieve,
                                        description="Number of images to retrieve from the search")
    include_base_images_in_preview: bool = Field(settings.query.include_base_images_in_preview,
                                                 description="Whether to include base images in the preview")
    verbose: bool = Field(True, description="Include Verbose results")
    generation_config: GenerationConfig = Field(..., description="Configuration for image generation")


class SearchResponse(BaseModel):
    results: List[str]
    qid: int
    preview_url: str
    base_images: Optional[List[str]] = None
    verbose_results : Optional[Dict[str, Any]] = None
    timings: Optional[Dict[str, Any]] = None


class GeneratorRequirement(BaseModel):
    name: str
    description: str


class GeneratorInfo(BaseModel):
    name: str
    description: str
    required_params: List[GeneratorRequirement]


class QueryLogEntry(BaseModel):
    qid: int
    query: str


class SearchLogsResponse(BaseModel):
    queries: List[QueryLogEntry]


class ServiceStatusResponse(BaseModel):
    status: str


class ServiceLogResponse(BaseModel):
    log: str
