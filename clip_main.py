import os
import pickle
from pathlib import Path

import clip
import numpy as np
import torch
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from tqdm import tqdm
# Load environment variables
load_dotenv()
RESOURCES_DIR = os.getenv('RESOURCES_DIR')

app = FastAPI()

# Load CLIP model
device = "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

embeddings = {}

origins = ["http://localhost:3000", "http://127.0.0.1:3000", os.getenv("PUBLIC_IP", "http://127.0.0.1:3000")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_images_from_directory(directory: str):
    image_paths = list(Path(directory).glob("*"))
    images = []
    for image_path in tqdm(image_paths):
        try:
            image = Image.open(image_path)
            images.append((image_path.stem, preprocess(image).unsqueeze(0).to(device)))
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
    return images


def convert_images_to_embeddings(images):
    embeddings = {}
    with torch.no_grad():
        for image_name, image in images:
            image_features = model.encode_image(image)
            embeddings[image_name] = image_features.cpu().numpy()
    return embeddings


def calculate_cosine_similarity(embedding1, embedding2):
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))


@app.on_event("startup")
async def startup_event():
    global embeddings
    embeddings_path = Path("./embeddings/embeddings_clip.pkl")

    if embeddings_path.exists():
        # Load embeddings from file
        with open(embeddings_path, "rb") as f:
            embeddings = pickle.load(f)
        print(f"Loaded embeddings from {embeddings_path}")
    else:
        # Load images
        images = load_images_from_directory(RESOURCES_DIR)
        print(f"Loaded {len(images)} images from {RESOURCES_DIR}")

        # Convert images to embeddings
        embeddings = convert_images_to_embeddings(images)
        print(f"Converted images to embeddings")

        # Store embeddings
        embeddings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(embeddings_path, "wb") as f:
            pickle.dump(embeddings, f)
        print(f"Stored embeddings to {embeddings_path}")


@app.get("/search")
async def search_images(query: str, n : int = 20):
    global embeddings

    # Convert query to embedding
    with torch.no_grad():
        text = clip.tokenize([query]).to(device)
        query_embedding = model.encode_text(text).cpu().numpy().flatten()

    # Compute cosine similarities
    similarities = []
    for image_name, image_embedding in embeddings.items():
        similarity = calculate_cosine_similarity(query_embedding, image_embedding.flatten())
        similarities.append((image_name, similarity))

    # Sort by similarity and get top 10 results
    similarities.sort(key=lambda x: x[1], reverse=True)
    top_results = similarities[:n]

    return {"results": [f"{image}.jpg" for image, _ in top_results]}


@app.get("/image/{image_name}")
async def get_image(image_name: str):
    image_path = Path(RESOURCES_DIR) / f"{image_name}"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)
