import io
import os
from collections import defaultdict

import requests
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from initialize import initialize_embeddings, hnsw_indices
from models import EmbedderManager, TileManager, Configuration, DALLEConnector

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


@app.on_event("startup")
def startup_event():
    initialize_embeddings()


@app.post("/find-neighbors/")
async def find_neighbors(file: UploadFile = File(...),
                         n: int = 20,
                         ef_search: int = 50):
    embedders = EmbedderManager.instance().get_embedders()
    tiles = TileManager.instance().load()

    neighbors_scores = defaultdict(float)
    for model_name, embedder in embedders.items():
        image = Image.open(file.file).convert("RGB")
        query_embedding = embedder.embed(image)

        hnsw_index = hnsw_indices[model_name]
        hnsw_index.hnsw.efSearch = ef_search
        _, indices = hnsw_index.search(query_embedding.reshape(1, -1), n)

        for i in indices[0]:
            neighbors_scores[i] += 1

    sorted_neighbors = sorted(neighbors_scores.items(), key=lambda x: x[1], reverse=True)
    top_filenames = [tiles[index].parent.filename for index, score in sorted_neighbors]

    return {"results": top_filenames}


@app.get("/search")
async def generate_and_find_neighbors(query: str, n: int = 20, k: int = 4, image_size: int = 1024, efSearch: int = 50):
    # connector = BingWrapperConnector()
    # crawled_images_response = connector.crawl_images(query, min_size=256, num_images=k)
    # generated_images = [requests.get(url).content for url in crawled_images_response["images"]]
    connector = DALLEConnector()
    res = connector.generate_image(prompt=query.replace(".", "").strip(), n=k)
    urls = [d["url"] for d in res["data"]]
    generated_images = [requests.get(url).content for url in urls]

    neighbors_scores = defaultdict(float)
    embedders = EmbedderManager.instance().get_embedders()
    tiles = TileManager.instance().load()

    for model_name, embedder in embedders.items():
        for image_data in generated_images:
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            query_embedding = embedder.embed(image)

            hnsw_index = hnsw_indices[model_name]
            hnsw_index.hnsw.efSearch = efSearch
            _, indices = hnsw_index.search(query_embedding.reshape(1, -1), n)

            for i in indices[0]:
                neighbors_scores[i] += 1

    sorted_neighbors = sorted(neighbors_scores.items(), key=lambda x: x[1], reverse=True)
    top_filenames = [tiles[index].parent.filename for index, score in sorted_neighbors]
    unique_filenames = []
    for f in top_filenames:
        if len(unique_filenames) >= n:
            break
        if f not in unique_filenames:
            unique_filenames.append(f)

    return {"results": unique_filenames, "base_image_urls": urls}


@app.get("/image/{filename}")
async def download_image(filename: str):
    file_path = os.path.join(Configuration.instance().resources_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")
