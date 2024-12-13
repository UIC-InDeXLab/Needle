import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ImageEmbedder(BaseModel):
    name: str
    model_name: str


class JSONConfig(BaseModel):
    weights_path: str
    image_embedders: List[ImageEmbedder]


class PostgresSettings(BaseModel):
    user: str = Field("myuser")
    password: str = Field("mypassword")
    host: str = Field("0.0.0.0")
    port: int = Field(5433)
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


class AppSettings(BaseModel):
    embedders_config_path: str = Field("config.json")
    use_cuda: bool = Field(False)
    recursive_indexing: bool = Field(False)
    batch_size: int = Field(100)
    num_embedding_workers: int = Field(4)
    num_watcher_workers: int = Field(4)


class IndexSettings(BaseModel):
    index_type: str = Field("HNSW")
    metric_type: str = Field("COSINE")


class GeneratorsSettings(BaseModel):
    host: str = Field("0.0.0.0")
    port: int = Field(8001)
    default_engine: str = Field("sdxl_lightning")

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class Settings(BaseSettings):
    # Environment-based settings
    postgres: PostgresSettings = PostgresSettings()
    milvus: MilvusSettings = MilvusSettings()
    app: AppSettings = AppSettings()
    generators: GeneratorsSettings = GeneratorsSettings()

    # JSON config
    json_config: Optional[JSONConfig] = None

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

    def load_json_config(self):
        """
        Load and parse the JSON configuration file specified in app.config_path.
        """
        config_path = Path(self.app.embedders_config_path)
        if config_path.exists():
            with open(config_path, "r") as file:
                json_data = json.load(file)
            self.json_config = JSONConfig(**json_data)
        else:
            raise FileNotFoundError(f"JSON config file not found at {config_path}")
