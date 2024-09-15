import json
import os
from abc import ABC, abstractmethod

import torch
from timm import create_model, data
from transformers import AutoModel, AutoTokenizer

from logger import logger
from models import Configuration
from models.singleton import Singleton


class ImageEmbedder(ABC):
    def __init__(self, device=torch.device("cpu")):
        self.model = create_model(self.model_name, pretrained=True, num_classes=0).to(device)
        self.model.eval()
        self.device = device
        self.preprocess = self.get_preprocess()
        self._weight = 1.0

    @property
    @abstractmethod
    def name(self):
        pass

    def get_preprocess(self):
        data_config = data.resolve_model_data_config(self.model)
        return data.create_transform(**data_config, is_training=False)

    @property
    def model_name(self) -> str:
        return Configuration.instance().get_image_embedder_details(self.name)["model_name"]

    @property
    def path(self) -> str:
        cman: Configuration = Configuration.instance()
        return cman.get_image_embedder_details(self.name)["path"].format(dataset=cman.dataset)

    def embed(self, img_binary):
        img_binary = self.preprocess(img_binary)
        img_binary = img_binary.unsqueeze(0).to(self.device)
        with torch.no_grad():
            embedding = self.model(img_binary).squeeze(0).cpu().numpy()
        return embedding

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


class EfficientNetEmbedder(ImageEmbedder):
    @property
    def name(self):
        return "efficientnet"


class RegNetEmbedder(ImageEmbedder):
    @property
    def name(self):
        return "regnet"


class MobileNetV4Embedder(ImageEmbedder):
    @property
    def name(self):
        return "mobilenetv4"


class Resnet50Embedder(ImageEmbedder):

    @property
    def name(self):
        return "resnet50"


class VitEmbedder(ImageEmbedder):

    @property
    def name(self):
        return "vit"


class EvaEmbedder(ImageEmbedder):
    @property
    def name(self):
        return "eva"


class ConvNextEmbedder(ImageEmbedder):
    @property
    def name(self):
        return "convnext"


_SUPPORTED_IMAGE_EMBEDDERS = [SwinTransformerEmbedder, EfficientNetEmbedder, RegNetEmbedder, MobileNetV4Embedder,
                              Resnet50Embedder, VitEmbedder, EvaEmbedder, ConvNextEmbedder]


class TextEmbedder(ABC):
    def __init__(self, device=torch.device("cpu")):
        self.device = device
        self.model = self.load_model().to(self.device)
        self.model.eval()
        self.tokenizer = self.get_tokenizer()

    @property
    @abstractmethod
    def name(self):
        pass

    def load_model(self):
        model_name = self.model_name
        model = AutoModel.from_pretrained(model_name)
        return model

    def get_tokenizer(self):
        model_name = self.model_name
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        return tokenizer

    @property
    def model_name(self) -> str:
        return Configuration.instance().get_text_embedder_details(self.name)["model_name"]

    def embed(self, text: str):
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).cpu().numpy()
        return embedding


class MiniLMTextEmbedder(TextEmbedder):
    @property
    def name(self):
        return "minilm"


@Singleton
class EmbedderManager:
    def __init__(self):
        self._image_embedder_classes = _SUPPORTED_IMAGE_EMBEDDERS
        self._device = torch.device(
            "cuda" if torch.cuda.is_available() and
                      str(os.getenv("USE_CUDA", "False")).strip().lower() in ["true", "t", "1"] else "cpu")
        self._image_embedders = {}
        for e in self._image_embedder_classes:
            embedder = e(device=self._device)
            self._image_embedders[embedder.name] = embedder

        self._init_embedders_weights()
        self._text_embedder = MiniLMTextEmbedder(device=self._device)

    def get_image_embedders(self):
        return self._image_embedders

    def get_image_embedder_by_name(self, name) -> ImageEmbedder:
        return self._image_embedders[name]

    def get_text_embedder(self) -> TextEmbedder:
        return self._text_embedder

    def _init_embedders_weights(self):
        path = Configuration.instance().weights_path
        weights = dict()
        default_weight = 1 / len(self._image_embedders)
        if os.path.exists(path):
            with open(path, 'r+') as file:
                weights = json.load(file)
                logger.info("Embedder weights loaded from file")

        for embedder_name, embedder in self._image_embedders.items():
            embedder.weight = weights.get(embedder_name, default_weight)

    def _save_embedder_weights(self):
        weights = {name: embedder.weight for name, embedder in self._image_embedders.items()}
        with open(Configuration.instance().weights_path, 'w+') as f:
            json.dump(weights, f)
        logger.info("Embedder weights dumped to the file")

    def finalize(self):
        self._save_embedder_weights()
