import json
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


def _default_data_dir() -> str:
    """Resolve the application data directory.

    Honours the NEEDLE_DATA_DIR environment variable so packaged desktop builds
    can point at a per-user location; defaults to ``~/.needle/data``.
    """
    env = os.environ.get("NEEDLE_DATA_DIR")
    if env:
        return env
    return str(Path.home() / ".needle" / "data")


class StorageSettings(BaseModel):
    """Filesystem locations for the embedded SQLite + LanceDB stores."""

    data_dir: str = Field(default_factory=_default_data_dir)

    def ensure_dirs(self) -> None:
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.lancedb_path).mkdir(parents=True, exist_ok=True)

    @property
    def sqlite_path(self) -> str:
        return str(Path(self.data_dir, "needle.db"))

    @property
    def sqlite_url(self) -> str:
        return f"sqlite:///{self.sqlite_path}"

    @property
    def lancedb_path(self) -> str:
        return str(Path(self.data_dir, "lancedb"))


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


class QuerySettings(BaseModel):
    num_images_to_retrieve: int = Field(20)
    num_images_to_generate: int = Field(4)
    generated_image_size: str = Field("MEDIUM")
    num_engines_to_use: int = Field(1)
    use_fallback: bool = Field(True)
    include_base_images_in_preview: bool = Field(False)


class DirectorySettings(BaseModel):
    num_watcher_workers: int = Field(4)
    # Kept small: the embedder models are large and indexing runs a full batch
    # through each of them in one forward pass. Big batches exhaust RAM/VRAM.
    batch_size: int = Field(8)
    recursive_indexing: bool = Field(False)
    consistency_check_interval: int = Field(1800)


class ServiceSettings(BaseModel):
    config_dir_path: str = Field("./configs/")
    use_cuda: bool = Field(False)


class ImageGeneratorSettings(BaseModel):
    host: str = Field("0.0.0.0")
    port: int = Field(8001)
    # Generation is delegated to the Needle Generator companion or an API
    # provider (no bundled model). "remote" is still accepted as an alias.
    default_engine: str = Field("needle-local")

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class Settings(BaseSettings):
    # Environment-based settings
    storage: StorageSettings = StorageSettings()
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
        Load the active embedders config.

        Prefers ``<data_dir>/embedders.json`` (written by the onboarding flow into a
        writable location) and falls back to the bundled default in the config dir.
        Missing config is tolerated (the app is simply "not configured" yet).
        """
        data_path = Path(self.storage.data_dir, "embedders.json")
        bundled_path = Path(self.service.config_dir_path, "embedders.json")
        config_path = data_path if data_path.exists() else bundled_path
        if config_path.exists():
            with open(config_path, "r") as file:
                json_data = json.load(file)
            self.embedders_config = EmbeddersConfig(**json_data)
        else:
            # Not configured yet (fresh install). Onboarding will write this later.
            self.embedders_config = None
