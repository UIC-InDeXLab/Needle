import os
from abc import ABC, abstractmethod

import torch
from timm import create_model
from torchvision import transforms
from typing import List, Dict, Union

from models import Configuration
from models.singleton import Singleton


class Embedder(ABC):
    def __init__(self, device=torch.device("cpu")):
        self.model = create_model(self.model_name, pretrained=True).to(device)
        self.model.eval()
        self.device = device
        self.preprocess = self.get_preprocess()

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def get_preprocess(self):
        pass

    @property
    def model_name(self) -> str:
        return Configuration.instance().get_embedder_details(self.name)["model_name"]

    @property
    def path(self) -> str:
        return Configuration.instance().get_embedder_details(self.name)["path"]

    def embed(self, img_binary):
        img_binary = self.preprocess(img_binary)
        img_binary = img_binary.unsqueeze(0).to(self.device)
        with torch.no_grad():
            embedding = self.model(img_binary).squeeze(0).cpu().numpy()
        return embedding


class SwinTransformerEmbedder(Embedder):
    @property
    def name(self):
        return "swin_transformer"

    def get_preprocess(self):
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])


class EfficientNetEmbedder(Embedder):
    @property
    def name(self):
        return "efficientnet"

    def get_preprocess(self):
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])


class RegNetEmbedder(Embedder):
    @property
    def name(self):
        return "regnet"

    def get_preprocess(self):
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])


@Singleton
class EmbedderManager:
    def __init__(self):
        self._embedder_classes = [SwinTransformerEmbedder, EfficientNetEmbedder, RegNetEmbedder]
        self._device = torch.device("cuda" if torch.cuda.is_available() and os.getenv("USE_CUDA", False) else "cpu")
        self._embedders = {}
        for e in self._embedder_classes:
            embedder = e(device=self._device)
            self._embedders[embedder.name] = embedder

    def get_embedders(self) -> dict[str, Union[SwinTransformerEmbedder, EfficientNetEmbedder, RegNetEmbedder]]:
        return self._embedders

    def get_embedder_by_name(self, name) -> Embedder:
        return self._embedders[name]
