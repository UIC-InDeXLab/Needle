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
    indexing_ratio: Optional[float] = None


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
    # Optional on purpose: when omitted the backend applies the saved generator
    # preferences, so every client resolves a search the same way. Supplying
    # engines explicitly is still allowed for one-off overrides.
    engines: Optional[List[EngineConfig]] = Field(
        None, description="Engines in priority order; defaults to the saved preferences")
    num_engines_to_use: int = Field(settings.query.num_engines_to_use, description="Number of engines to use")
    num_images: int = Field(settings.query.num_images_to_generate,
                            description="Number of images to generate per engine")
    image_size: str = Field(settings.query.generated_image_size, description="Image size in pixels")
    use_fallback: Optional[bool] = Field(
        None, description="Override the saved fallback setting for this search")


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
    available: bool = True
    requires_credentials: bool = False
    credentials_set: bool = True


class SetCredentialsRequest(BaseModel):
    params: Dict[str, str] = Field(..., description="Credential key/value pairs (e.g. api_key)")


class GeneratorPreference(BaseModel):
    name: str = Field(..., description="Engine id, e.g. needle-local")
    enabled: bool = Field(False, description="Use this engine for search")
    params: Dict[str, Any] = Field(default_factory=dict,
                                   description="Per-engine settings, e.g. the model to use")


class GeneratorPreferencesRequest(BaseModel):
    engines: List[GeneratorPreference] = Field(
        ..., description="Engines in priority order; the first enabled one is tried first")
    fallback: bool = Field(True, description="On failure, fall through to the next enabled engine")


class ConfigureSetupRequest(BaseModel):
    profile: str = Field(..., description="Embedder profile: fast | balanced | accurate")
    use_gpu: bool = Field(False, description="Enable GPU (CUDA/MPS) for embeddings and generation")


class SetGpuRequest(BaseModel):
    use_gpu: bool = Field(..., description="Enable GPU (CUDA/MPS) for embeddings and generation")


class LoadModelRequest(BaseModel):
    model: str = Field(..., description="On-device generation model id, e.g. sd-turbo")


class GenerateImagesRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt")
    model: Optional[str] = Field(None, description="Model id; defaults to the fastest one")
    num_images: int = Field(1, ge=1, le=8, description="How many images to generate")
    size: str = Field("MEDIUM", description="Named size: SMALL | MEDIUM | LARGE")
    width: Optional[int] = Field(None, ge=128, le=1536)
    height: Optional[int] = Field(None, ge=128, le=1536)
    steps: Optional[int] = Field(None, ge=1, le=50, description="Denoising steps")
    seed: Optional[int] = Field(None, description="Seed for reproducible output; omit for random")


class SaveImageRequest(BaseModel):
    image: str = Field(..., description="PNG image as a base64 string or data URL")
    directory: str = Field(..., description="Destination folder chosen by the user")
    filename: Optional[str] = Field(None, description="Preferred file name (without extension)")


class QueryLogEntry(BaseModel):
    qid: int
    query: str


class SearchLogsResponse(BaseModel):
    queries: List[QueryLogEntry]


class ServiceStatusResponse(BaseModel):
    status: str


class ServiceLogResponse(BaseModel):
    log: str


# Variance Analysis Schemas
class GeneratePoolRequest(BaseModel):
    query: str = Field(..., description="Query string")
    pool_size: int = Field(20, description="Number of guide images to generate (M_pool)")
    generation_config: GenerationConfig = Field(..., description="Configuration for image generation")


class EmbeddingData(BaseModel):
    embedder_name: str
    embedding: List[float]


class GuideImageData(BaseModel):
    image_index: int
    base64_image: str
    embeddings: List[EmbeddingData]


class GeneratePoolResponse(BaseModel):
    query: str
    pool_size: int
    guide_images: List[GuideImageData]
    embedder_names: List[str]


# Embedding computation schemas
class ComputeEmbeddingsRequest(BaseModel):
    image_paths: List[str] = Field(..., description="List of file paths to images")


class ImageEmbeddingsResponse(BaseModel):
    image_path: str
    embeddings: List[EmbeddingData]


class ComputeEmbeddingsResponse(BaseModel):
    results: List[ImageEmbeddingsResponse]
    embedder_names: List[str]
