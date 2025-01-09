import torch
from timm import create_model, data

from core.singleton import Singleton
from settings import settings


class ImageEmbedder:
    def __init__(self, name, model_name, weight, device=torch.device("cpu")):
        self._name = name
        self._model_name = model_name
        self._device = device
        self._weight = weight

        self.model = create_model(model_name, pretrained=True, num_classes=0).to(device)
        self.model.eval()

        self.preprocess = self.get_preprocess()
        self._weight = 1.0
        self._embedding_dim = self._determine_embedding_dim()

    def get_preprocess(self):
        data_config = data.resolve_model_data_config(self.model)
        return data.create_transform(**data_config, is_training=False)

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> torch.device:
        return self._device

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
