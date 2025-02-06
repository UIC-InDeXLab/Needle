from monitoring import logger

from .settings_model import Settings


class ReadOnlySettings:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._settings = Settings()
            cls._instance._settings.load_embedders_config()
            cls._log_settings()
        return cls._instance

    @classmethod
    def _log_settings(cls):
        logger.info("Settings Loaded:")
        logger.info(f"Postgres Settings: {cls._instance._settings.postgres}")
        logger.info(f"Milvus Settings: {cls._instance._settings.milvus}")
        logger.info(f"Service Settings: {cls._instance._settings.service}")
        logger.info(f"Directory Settings: {cls._instance._settings.directory}")
        logger.info(f"Query Settings: {cls._instance._settings.query}")
        logger.info(f"Generators Settings: {cls._instance._settings.generator}")
        if cls._instance._settings.embedders_config:
            logger.info(f"Embedders Config: {cls._instance._settings.embedders_config.dict()}")

    @property
    def postgres(self):
        return self._settings.postgres

    @property
    def milvus(self):
        return self._settings.milvus

    @property
    def service(self):
        return self._settings.service

    @property
    def query(self):
        return self._settings.query

    @property
    def directory(self):
        return self._settings.directory

    @property
    def generators(self):
        return self._settings.generator

    @property
    def image_embedders(self):
        return self._settings.embedders_config.image_embedders

    def get_image_embedder_details(self, name: str):
        embedder = next(
            (e for e in self._settings.embedders_config.image_embedders if
             e.name.strip().lower() == name.strip().lower()),
            None
        )
        if not embedder:
            raise ValueError(f"Image embedder with name '{name}' not found.")
        return embedder.dict()
