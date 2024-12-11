import json
import os
from abc import ABC, abstractmethod

import torch
from timm import create_model, data

from core.singleton import Singleton
from settings import settings


class ImageEmbedder(ABC):
    def __init__(self, device=torch.device("cpu")):
        self.model = create_model(self.model_name, pretrained=True, num_classes=0).to(device)
        self.model.eval()
        self.device = device
        self.preprocess = self.get_preprocess()
        self._weight = 1.0
        self._embedding_dim = self._determine_embedding_dim()

    @property
    @abstractmethod
    def name(self):
        pass

    def get_preprocess(self):
        data_config = data.resolve_model_data_config(self.model)
        return data.create_transform(**data_config, is_training=False)

    @property
    def model_name(self) -> str:
        return settings.get_image_embedder_details(self.name)["model_name"]

    @property
    def path(self) -> str:
        return settings.get_image_embedder_details(self.name)["path"].format(dataset=settings.dataset)

    def embed(self, img_binary):
        img_binary = self.preprocess(img_binary)
        img_binary = img_binary.unsqueeze(0).to(self.device)
        with torch.no_grad():
            embedding = self.model(img_binary).squeeze(0).cpu().numpy()
        return embedding

    def _determine_embedding_dim(self):
        # Generate a dummy image tensor to determine the output dimension of the embedder
        dummy_input = torch.zeros((3, 224, 224)).to(self.device)  # Assuming the input size is 3x224x224
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

    @weight.setter
    def weight(self, value):
        self._weight = value


class SwinTransformerEmbedder(ImageEmbedder):
    @property
    def name(self):
        return "swin_transformer"


class RegNetEmbedder(ImageEmbedder):
    @property
    def name(self):
        return "regnet"


class VitEmbedder(ImageEmbedder):

    @property
    def name(self):
        return "vit"


class EvaEmbedder(ImageEmbedder):
    @property
    def name(self):
        return "eva"


_SUPPORTED_IMAGE_EMBEDDERS = [SwinTransformerEmbedder, RegNetEmbedder, VitEmbedder, EvaEmbedder]


@Singleton
class EmbedderManager:
    def __init__(self):
        self._image_embedder_classes = _SUPPORTED_IMAGE_EMBEDDERS
        self._device = torch.device(
            "cuda" if torch.cuda.is_available() and settings.app.use_cuda else "cpu")
        self._image_embedders = {}
        for e in self._image_embedder_classes:
            embedder = e(device=self._device)
            self._image_embedders[embedder.name] = embedder

        self._init_embedders_weights()

    def get_image_embedders(self):
        return self._image_embedders

    def get_image_embedder_by_name(self, name) -> ImageEmbedder:
        return self._image_embedders[name]

    def _init_embedders_weights(self):
        path = settings.weights_path
        weights = dict()
        default_weight = 1 / len(self._image_embedders)
        if os.path.exists(path):
            with open(path, 'r+') as file:
                weights = json.load(file)
                # logger.info("Embedder weights loaded from file")

        for embedder_name, embedder in self._image_embedders.items():
            embedder.weight = weights.get(embedder_name, default_weight)

    def _save_embedder_weights(self):
        weights = {name: embedder.weight for name, embedder in self._image_embedders.items()}
        with open(settings.weights_path, 'w+') as f:
            json.dump(weights, f)
        # logger.info("Embedder weights dumped to the file")

    def finalize(self):
        self._save_embedder_weights()
