import os

import numpy as np
from tqdm import tqdm

from models import Configuration, ImageFile, TileManager
from models.embedders import EmbedderManager
from utils import load_embeddings, save_embeddings, create_hnsw_index, get_tiles

hnsw_indices = {}


def initialize_embeddings():
    global hnsw_indices
    cman, tman, eman = Configuration.instance(), TileManager.instance(), EmbedderManager.instance()
    for embedder_name, embedder in eman.get_embedders().items():
        if os.path.exists(embedder.path):
            embeddings = load_embeddings(embedder.path)
        else:
            embeddings = []
            for filename in tqdm(os.listdir(cman.resources_dir)):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    image = ImageFile(filename)
                    image_tiles = get_tiles(image)
                    for tile in image_tiles:
                        embedding = embedder.embed(tile.bin)
                        tile.vector_index = len(embeddings)
                        tile.clean_binary()
                        embeddings.append(embedding)
                        if embedder_name == "swin_transformer":
                            tman.add_tile(tile)
            embeddings = np.array(embeddings)
            save_embeddings(embedder.path, embeddings)
        tman.save()

        hnsw_indices[embedder_name] = create_hnsw_index(embeddings)
