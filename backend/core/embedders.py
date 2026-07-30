import platform

import torch
import torch.nn as nn
from core.singleton import Singleton
from monitoring import logger
from settings import settings
from timm import create_model, data


class ImageEmbedder:
    def __init__(self, name, model_name, weight, device=torch.device("cpu")):
        self._name = name
        self._model_name = model_name
        self._device = device
        self._weight = weight

        # Create and move the model to the device.
        model = create_model(model_name, pretrained=True, num_classes=0).to(device)

        # Wrap the model with DataParallel if more than one CUDA GPU is available.
        if device.type == "cuda" and torch.cuda.device_count() > 1:
            self.model = nn.DataParallel(model)
        else:
            self.model = model

        self.model.eval()

        # Use the unwrapped model for configuration
        self.preprocess = self.get_preprocess()
        self._embedding_dim = self._determine_embedding_dim()

    def get_preprocess(self):
        # Unwrap the model if wrapped in DataParallel
        model_for_config = self.model.module if hasattr(self.model, 'module') else self.model
        data_config = data.resolve_model_data_config(model_for_config)
        return data.create_transform(**data_config, is_training=False)

    def embed(self, img_binary):
        # Preprocess the image and add batch dimension.
        img_tensor = self.preprocess(img_binary)
        img_tensor = img_tensor.unsqueeze(0).to(self.device)
        with torch.no_grad():
            # DataParallel will split the batch across GPUs.
            embedding = self.model(img_tensor).squeeze(0).cpu().numpy()
        return embedding

    def _determine_embedding_dim(self):
        # Unwrap the model to get the proper configuration.
        model_for_config = self.model.module if hasattr(self.model, 'module') else self.model
        data_config = data.resolve_model_data_config(model_for_config)
        # Get the expected input size from the configuration; defaults to (3,224,224)
        input_size = data_config.get("input_size", (3, 224, 224))

        # Create a dummy input tensor with the correct size.
        dummy_input = torch.zeros(input_size).to(self.device)
        dummy_input = self.preprocess(dummy_input).unsqueeze(0).to(self.device)
        with torch.no_grad():
            embedding = self.model(dummy_input).squeeze(0).cpu().numpy()
        return embedding.shape[0]

    @property
    def embedding_dim(self):
        return self._embedding_dim

    @property
    def weight(self):
        return self._weight

    @property
    def device(self):
        return self._device


@Singleton
class EmbedderManager:
    """Lazily manages image embedders.

    Models are NOT loaded at construction — that would make first launch heavy and
    can exhaust memory before the user has chosen a profile. Call ``load()`` (driven
    by the onboarding/setup flow) to actually instantiate the models.
    """

    def __init__(self):
        self._image_embedders = {}
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    def load(self, progress=None):
        """Instantiate embedders from the current settings. Heavy: downloads/loads weights.

        ``progress`` is an optional callback ``(index, total, name)`` invoked before
        each model loads, so the UI can show onboarding progress.
        """
        from core.device import select_device

        device = select_device()
        configs = list(settings.image_embedders)
        total = len(configs)
        embedders = {}
        for i, cfg in enumerate(configs):
            if progress:
                progress(i, total, cfg.name)
            logger.info(f"Loading embedder {i + 1}/{total}: {cfg.name} ({cfg.model_name}) on {device}")
            embedders[cfg.name] = ImageEmbedder(
                name=cfg.name,
                model_name=cfg.model_name,
                weight=cfg.weight if cfg.weight is not None else 1 / total,
                device=device,
            )
        self._image_embedders = embedders
        self._loaded = True
        logger.info(f"Loaded {total} embedder(s) on {device}")
        return self._image_embedders

    def unload(self):
        self._image_embedders = {}
        self._loaded = False

    def get_image_embedders(self):
        return self._image_embedders

    def get_image_embedder_by_name(self, name) -> ImageEmbedder:
        return self._image_embedders[name]
