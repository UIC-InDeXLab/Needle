from typing import List

import requests
import os
import pickle
import numpy as np
from PIL import Image
import faiss

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


def get_tiles(image: ImageFile, min_patch_size=256) -> List[Tile]:
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


def create_hnsw_index(embeddings, m=64, ef_construction=200):
    dim = embeddings.shape[1]
    index = faiss.IndexHNSWFlat(dim, m)
    index.hnsw.efConstruction = ef_construction
    index.add(embeddings)
    return index
