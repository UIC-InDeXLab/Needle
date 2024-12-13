import logging

from .settings_model import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReadOnlySettings")


class ReadOnlySettings:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._settings = Settings()
            cls._instance._settings.load_json_config()
            cls._log_settings()
        return cls._instance

    @classmethod
    def _log_settings(cls):
        logger.info("Settings Loaded:")
        logger.info(f"Postgres Settings: {cls._instance._settings.postgres}")
        logger.info(f"Milvus Settings: {cls._instance._settings.milvus}")
        logger.info(f"App Settings: {cls._instance._settings.app}")
        logger.info(f"Generators Settings: {cls._instance._settings.generators}")
        if cls._instance._settings.json_config:
            logger.info(f"JSON Config: {cls._instance._settings.json_config.dict()}")

    @property
    def postgres(self):
        return self._settings.postgres

    @property
    def milvus(self):
        return self._settings.milvus

    @property
    def app(self):
        return self._settings.app

    @property
    def generators(self):
        return self._settings.generators

    @property
    def json_config(self):
        if not self._settings.json_config:
            raise RuntimeError("JSON configuration is not loaded.")
        return self._settings.json_config

    @property
    def embedders(self):
        return {
            "image_embedders": [embedder.model_dump() for embedder in self.json_config.image_embedders],
            "text_embedders": [embedder.model_dump() for embedder in self.json_config.text_embedders],
        }

    @property
    def weights_path(self):
        return self.json_config.weights_path


    def get_image_embedder_details(self, name: str):
        embedder = next(
            (e for e in self.json_config.image_embedders if e.name.strip().lower() == name.strip().lower()),
            None
        )
        if not embedder:
            raise ValueError(f"Image embedder with name '{name}' not found.")
        return embedder.dict()
