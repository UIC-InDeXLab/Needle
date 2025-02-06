import torch
from timm import create_model, data
from core.singleton import Singleton
from settings import settings
import torch.nn as nn


class ImageEmbedder:
    def __init__(self, name, model_name, weight, device=torch.device("cpu")):
        self._name = name
        self._model_name = model_name
        self._device = device
        self._weight = weight

        # Create and move the model to the device.
        model = create_model(model_name, pretrained=True, num_classes=0).to(device)

        # Wrap the model with DataParallel if more than one GPU is available.
        if torch.cuda.is_available() and torch.cuda.device_count() > 1 and settings.service.use_cuda:
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
    def __init__(self):
        self._device = torch.device(
            "cuda" if torch.cuda.is_available() and settings.service.use_cuda else "cpu")
        self._image_embedders = {}
        for embedder_config in settings.image_embedders:
            self._image_embedders[embedder_config.name] = ImageEmbedder(
                name=embedder_config.name,
                model_name=embedder_config.model_name,
                weight=embedder_config.weight if embedder_config.weight is not None
                else 1 / len(settings.image_embedders),
                device=self._device)

    def get_image_embedders(self):
        return self._image_embedders

    def get_image_embedder_by_name(self, name) -> ImageEmbedder:
        return self._image_embedders[name]
