from monitoring import logger
from typing import Dict, List
from PIL import Image as PImage
import torch
from core import embedder_manager

class EmbedderService:
    def __init__(self):
        # Do NOT cache the embedders dict here: ``embedder_manager.load()``
        # reassigns its internal dict when models finish loading, so a value
        # captured at construction time can become permanently stale (empty).
        # Always read the current embedders live via the ``embedders`` property.
        pass

    @property
    def embedders(self):
        return embedder_manager.get_image_embedders()

    def compute_batch_embeddings(self, image_paths: List[str]) -> Dict[str, Dict[str, List[float]]]:
        # Load images from disk
        images = []
        for path in image_paths:
            try:
                img = PImage.open(path).convert("RGB")
                images.append(img)
                logger.debug(f"Loaded image: {path}")
            except Exception as e:
                logger.error(f"Error loading image {path}: {e}", exc_info=True)
                images.append(None)  # Placeholder in case of failure

        # For each embedder, process all images at once
        batch_embeddings = {}
        for embedder_name, embedder in self.embedders.items():
            try:
                # Preprocess each image; if an image failed to load, replace it with a zero tensor
                processed = []
                for img in images:
                    if img is not None:
                        processed.append(embedder.preprocess(img))
                    else:
                        # Create a zero tensor with the expected input shape.
                        # If available, retrieve the expected input size from the model's config.
                        # For simplicity, we assume a fallback size of (3, 224, 224)
                        processed.append(torch.zeros((3, 224, 224)))
                # Stack the processed images into a batch tensor
                batch = torch.stack(processed, dim=0).to(embedder.device)

                with torch.inference_mode():
                    # Forward pass: DataParallel will split the batch among GPUs if applicable
                    output = embedder.model(batch)
                # Assume output shape is [batch_size, embedding_dim]
                embeddings_np = output.detach().cpu().numpy()
                # Convert each sample's embedding to a list
                embeddings_list = embeddings_np.tolist()
                batch_embeddings[embedder_name] = embeddings_list
                logger.debug(f"Computed batch embeddings for embedder {embedder_name}")
                # Release activations/inputs promptly so peak memory stays bounded
                # when several large models run over the same batch.
                del batch, output, embeddings_np, processed
                if embedder.device.type == "cuda":
                    torch.cuda.empty_cache()
            except Exception as e:
                logger.error(f"Error processing batch with embedder {embedder_name}: {e}", exc_info=True)
                batch_embeddings[embedder_name] = [None] * len(image_paths)

        # Combine the results per image path:
        # Create a dictionary mapping each image path to a dictionary that maps embedder names to embeddings.
        embeddings = {}
        for idx, path in enumerate(image_paths):
            embeddings[path] = {embedder_name: batch_embeddings[embedder_name][idx]
                                for embedder_name in self.embedders.keys()}
        return embeddings
