import os
import pickle
from collections import defaultdict
from typing import List

import hnswlib
import numpy as np
import requests

from sklearn.decomposition import PCA

from models.image import ImageFile
from models.tile import Tile


def load_embeddings(embeddings_file):
    with open(embeddings_file, "rb") as f:
        embeddings = pickle.load(f)
    return embeddings


def save_embeddings(embeddings_file, embeddings):
    with open(embeddings_file, "wb") as f:
        pickle.dump(embeddings, f)


def load_tiles(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return pickle.load(f)
    return []


def save_tiles(file_path, mapping):
    with open(file_path, "wb") as f:
        pickle.dump(mapping, f)


def get_image_from_url(url):
    return requests.get(url).content


def get_tiles(image: ImageFile, min_patch_size=448) -> List[Tile]:
    width, height = image.bin.size
    tiles, cameras = [], []

    def divide_until_not_less_than_k(i, k):
        while i >= 2 * k:
            i /= 2
        return int(i)

    def crop_frames(frame_width, frame_height):
        if frame_width > width or frame_height > height:
            return

        if (frame_width, frame_height) in cameras:
            crop_frames(frame_width * 2, frame_height)
            crop_frames(frame_width, frame_height * 2)
        else:
            cameras.append((frame_width, frame_height))
            for x in range(0, width, frame_width):
                for y in range(0, height, frame_height):
                    box = (x, y, min(x + frame_width, width), min(y + frame_height, height))
                    patch = image.bin.crop(box)
                    tile = Tile(patch, image, len(tiles))
                    tiles.append(tile)
            crop_frames(frame_width * 2, frame_height)
            crop_frames(frame_width, frame_height * 2)

    min_width = divide_until_not_less_than_k(width, min_patch_size)
    min_height = divide_until_not_less_than_k(height, min_patch_size)
    crop_frames(min_width, min_height)
    return tiles


def create_hnsw_index(embeddings, m=64, ef_construction=300, dim=None, ids=None):
    dim = embeddings.shape[1] if not dim else dim
    p = hnswlib.Index(space='cosine', dim=dim)
    p.init_index(max_elements=500000, ef_construction=ef_construction, M=m)
    if embeddings.size != 0:
        p.add_items(embeddings, ids=ids)

    p.set_ef(300)
    # index = faiss.IndexHNSWFlat(dim, m)
    # index.metric_type = faiss.METRIC_INNER_PRODUCT
    # index.hnsw.efConstruction = ef_construction
    # index.add(embeddings)
    return p


def aggregate_rankings(rankers_results, weights, k):
    scores = {}
    for i, R_i in enumerate(rankers_results):
        for j, result in enumerate(R_i):
            if result not in scores:
                scores[result] = 0
            scores[result] += weights[i] * (1 / (j + 1))

    ranked_results = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    return ranked_results[:k]
