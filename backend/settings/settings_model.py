import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ImageEmbedder(BaseModel):
    name: str
    model_name: str
    weight: float


class EmbeddersConfig(BaseModel):
    image_embedders: List[ImageEmbedder]


class PostgresSettings(BaseModel):
    user: str = Field("myuser")
    password: str = Field("mypassword")
    host: str = Field("0.0.0.0")
    port: int = Field(5432)
    db: str = Field("mydb")

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class MilvusSettings(BaseModel):
    host: str = Field("0.0.0.0")
    port: int = Field(19530)

    @property
    def uri(self) -> str:
        return f"{self.host}:{self.port}"


class QuerySettings(BaseModel):
    num_images_to_retrieve: int = Field(20)
    num_images_to_generate: int = Field(4)
    generated_image_size: str = Field("MEDIUM")
    num_engines_to_use: int = Field(1)
    use_fallback: bool = Field(True)
    include_base_images_in_preview: bool = Field(False)


class DirectorySettings(BaseModel):
    num_watcher_workers: int = Field(4)
    batch_size: int = Field(50)
    recursive_indexing: bool = Field(False)
    consistency_check_interval: int = Field(1800)


class ServiceSettings(BaseModel):
    config_dir_path: str = Field("./configs/")
    use_cuda: bool = Field(False)


class ImageGeneratorSettings(BaseModel):
    host: str = Field("0.0.0.0")
    port: int = Field(8001)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class Settings(BaseSettings):
    # Environment-based settings
    postgres: PostgresSettings = PostgresSettings()
    milvus: MilvusSettings = MilvusSettings()
    service: ServiceSettings = ServiceSettings()
    generator: ImageGeneratorSettings = ImageGeneratorSettings()
    directory: DirectorySettings = DirectorySettings()
    query: QuerySettings = QuerySettings()

    # JSON config
    embedders_config: Optional[EmbeddersConfig] = None

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

    def load_embedders_config(self):
        """
        Load and parse the JSON configuration file specified in app.config_path.
        """
        config_path = Path(self.service.config_dir_path, "embedders.json")
        if config_path.exists():
            with open(config_path, "r") as file:
                json_data = json.load(file)
            self.embedders_config = EmbeddersConfig(**json_data)
        else:
            raise FileNotFoundError(f"JSON config file not found at {config_path}")
