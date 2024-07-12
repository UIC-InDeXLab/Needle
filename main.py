import io
import os
import pickle
from collections import defaultdict
from pathlib import Path

import faiss
import numpy as np
import torch
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from torchvision import models, transforms
from tqdm import tqdm

from connectors import StableDiffusionXLConnector

load_dotenv()

app = FastAPI()

origins = ["http://localhost:3000", "http://127.0.0.1:3000", os.getenv("PUBLIC_IP", "http://127.0.0.1:3000")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory containing images
RESOURCES_DIR = os.getenv('RESOURCES_DIR')
# Files to store embeddings
EMBEDDINGS_FILES = {
    "resnet50": "./embeddings/embeddings_resnet50.pkl",
    "vgg16": "./embeddings/embeddings_vgg16.pkl",
    "inceptionv3": "./embeddings/embeddings_inceptionv3.pkl",
    "mobilenetv2": "./embeddings/embeddings_mobilenetv2.pkl",
}
# File to store the index to filename mapping
INDEX_TO_FILENAME_FILE = "./embeddings/index_to_filename.pkl"

# Dimension of the embeddings for each model
EMBEDDING_DIMS = {
    "resnet50": 1000,
    "vgg16": 1000,
    "inceptionv3": 1000,
    "mobilenetv2": 1000,
}

# Initialize FAISS indices
indices = {
    model_name: faiss.IndexLSH(EMBEDDING_DIMS[model_name], EMBEDDING_DIMS[model_name] * 4)
    for model_name in EMBEDDING_DIMS
}

# Load the pre-trained models
models_dict = {
    "resnet50": models.resnet50(pretrained=True),
    "vgg16": models.vgg16(pretrained=True),
    "inceptionv3": models.inception_v3(pretrained=True),
    "mobilenetv2": models.mobilenet_v2(pretrained=True),
}

# Set models to evaluation mode
for model in models_dict.values():
    model.eval()

# Define transformations for each model
preprocess_dict = {
    "resnet50": transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]),
    "vgg16": transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]),
    "inceptionv3": transforms.Compose([
        transforms.Resize(299),
        transforms.CenterCrop(299),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]),
    "mobilenetv2": transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]),
}

# Initialize the index-to-filename mapping
index_to_filename = []


def get_image_embedding(image_path, model, preprocess):
    image = Image.open(image_path).convert("RGB")
    image = preprocess(image)
    image = image.unsqueeze(0)  # add batch dimension
    with torch.no_grad():
        embedding = model(image).squeeze(0).numpy()
    return embedding


def load_embeddings(embeddings_file):
    with open(embeddings_file, "rb") as f:
        embeddings = pickle.load(f)
    return embeddings


def save_embeddings(embeddings_file, embeddings):
    with open(embeddings_file, "wb") as f:
        pickle.dump(embeddings, f)


def load_index_to_filename():
    if os.path.exists(INDEX_TO_FILENAME_FILE):
        with open(INDEX_TO_FILENAME_FILE, "rb") as f:
            return pickle.load(f)
    return []


def save_index_to_filename(mapping):
    with open(INDEX_TO_FILENAME_FILE, "wb") as f:
        pickle.dump(mapping, f)


@app.on_event("startup")
def initialize_embeddings():
    global index_to_filename
    index_to_filename = load_index_to_filename()
    for model_name, model in models_dict.items():
        if os.path.exists(EMBEDDINGS_FILES[model_name]):
            embeddings = load_embeddings(EMBEDDINGS_FILES[model_name])
        else:
            embeddings = []
            for filename in tqdm(os.listdir(RESOURCES_DIR)):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    image_path = os.path.join(RESOURCES_DIR, filename)
                    embedding = get_image_embedding(image_path, model, preprocess_dict[model_name])
                    embeddings.append(embedding)
                    if model_name == "resnet50":  # Only need to map filenames once
                        index_to_filename.append(filename)
            embeddings = np.array(embeddings)
            save_embeddings(EMBEDDINGS_FILES[model_name], embeddings)
        indices[model_name].add(embeddings)
    save_index_to_filename(index_to_filename)


@app.post("/find-neighbors/")
async def find_neighbors(file: UploadFile = File(...), n: int = 20):
    neighbors_count = defaultdict(int)
    for model_name, model in models_dict.items():
        image = Image.open(file.file).convert("RGB")
        image = preprocess_dict[model_name](image)
        image = image.unsqueeze(0)  # add batch dimension
        with torch.no_grad():
            embedding = model(image).squeeze(0).numpy()

        D, I = indices[model_name].search(np.array([embedding]), k=n)
        for index in I[0]:
            neighbors_count[index] += 1

    # Sort by frequency and get the top 5
    sorted_neighbors = sorted(neighbors_count.items(), key=lambda x: x[1], reverse=True)[:n]
    top_neighbors = [index for index, count in sorted_neighbors]

    top_filenames = [index_to_filename[index] for index in top_neighbors]

    return {"results": top_filenames}


@app.get("/search")
async def generate_and_find_neighbors(query: str, n: int = 20, k: int = 4, image_size: int = 1024):
    connector = StableDiffusionXLConnector()
    generated_images = [connector.generate_image(query, size=image_size) for _ in range(k)]

    neighbors_count = defaultdict(int)
    for model_name, model in models_dict.items():
        for image_png_binary in generated_images:
            image = Image.open(io.BytesIO(image_png_binary)).convert("RGB")
            image = preprocess_dict[model_name](image)
            image = image.unsqueeze(0)  # add batch dimension
            with torch.no_grad():
                embedding = model(image).squeeze(0).numpy()

            D, I = indices[model_name].search(np.array([embedding]), k=n)  # Find 5 nearest neighbors
            for index in I[0]:
                neighbors_count[index] += 1

    # Sort by frequency and get the top 5
    sorted_neighbors = sorted(neighbors_count.items(), key=lambda x: x[1], reverse=True)[:n]
    top_neighbors = [index for index, count in sorted_neighbors]

    top_filenames = [index_to_filename[index] for index in top_neighbors]

    return {"results": top_filenames}


@app.get("/image/{image_name}")
async def get_image(image_name: str):
    image_path = Path(RESOURCES_DIR) / f"{image_name}"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)
