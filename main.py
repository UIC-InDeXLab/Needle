import io
import os
import sys
from collections import defaultdict
from contextlib import asynccontextmanager

import numpy as np
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Dict

from initialize import initialize_embeddings, hnsw_indices
from models import EmbedderManager, TileManager, Configuration, LocalStableDiffusionConnector
from models.connectors import EngineManager
from models.embedders import TextEmbedder, ImageEmbedder
from models.query import QueryManager, Query
from utils import fagin_algorithm, aggregate_rankings
from logger import logger

load_dotenv()

origins = ["http://localhost:3000", "http://127.0.0.1:3000", os.getenv("PUBLIC_IP", "http://127.0.0.1:3000")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_embeddings()
    yield
    eman: EmbedderManager = EmbedderManager.instance()
    eman.finalize()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/find-neighbors/")
async def find_neighbors(file: UploadFile = File(...),
                         n: int = 20):
    embedders = EmbedderManager.instance().get_image_embedders()
    tiles = TileManager.instance().load()

    results = {}
    for model_name, embedder in embedders.items():
        results[model_name] = []
        image = Image.open(file.file).convert("RGB")
        query_embedding = np.array([embedder.embed(image)])
        hnsw_index = hnsw_indices[model_name]
        # hnsw_index.hnsw.efSearch = ef_search
        # distances, indices = hnsw_index.search(query_embedding, n)
        labels, distances = hnsw_index.knn_query(query_embedding, k=4 * n)

        for tile_idx, distance in zip(labels[0], distances[0]):
            results[model_name].append((tile_idx, 1 - distance))

    top_tiles = fagin_algorithm(list(results.values()), k=4 * n)
    top_filenames = [tiles[index].parent.filename for index in top_tiles]
    unique_filenames = list(dict.fromkeys(top_filenames))
    return {"results": unique_filenames[:n]}


@app.get("/search")
async def generate_and_find_neighbors(query: str, n: int = 20, k: int = 4, image_size: int = 512,
                                      generator_engine: str = "stable-diffusion"):
    query_object = Query(query)

    qman: QueryManager = QueryManager.instance()
    qid = qman.add_query(query_object)
    # connector = BingWrapperConnector()
    # crawled_images_response = connector.crawl_images(query, min_size=256, num_images=k)
    # generated_images = [requests.get(url).content for url in crawled_images_response["images"]]

    # connector = DALLEConnector()
    # res = connector.generate_image(prompt=query.replace(".", "").strip(), n=k)
    # urls = [d["url"] for d in res["data"]]
    # generated_images = [requests.get(url).content for url in urls]

    urls = []
    connector = LocalStableDiffusionConnector()
    generated_images = [connector.generate_image(f"a {query.strip()}", size=image_size) for _ in range(k)]

    embedders = EmbedderManager.instance().get_image_embedders()
    tiles = TileManager.instance().tiles

    results = {}
    ranking_weights = []
    for embedder_name, embedder in embedders.items():
        for i, image_data in enumerate(generated_images):
            results[f"{embedder_name}_{i}"] = []
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            query_embedding = np.array([embedder.embed(image)])
            hnsw_index = hnsw_indices[embedder_name]
            labels, distances = hnsw_index.knn_query(query_embedding, k=4 * n)

            for tile_idx in labels[0]:
                results[f"{embedder_name}_{i}"].append(tile_idx)

        rankings = [ranking for e, ranking in results.items() if e.startswith(embedder_name)]
        embedder_top_tiles = aggregate_rankings(rankings, weights=[1] * len(generated_images), k=4 * n)
        embedder_top_images = [tiles[index].parent.filename for index in embedder_top_tiles]
        embedder_top_unique_images = list(dict.fromkeys(embedder_top_images))
        query_object.add_embedder_results(embedder_name=embedder_name, results=embedder_top_unique_images)
        for r in rankings:
            ranking_weights.append((r, embedder.weight))

    top_tiles = aggregate_rankings(rankers_results=[r for r, w in ranking_weights],
                                   weights=[w for r, w in ranking_weights], k=4 * n)
    top_images = [tiles[index].parent.filename for index in top_tiles]
    top_files = list(dict.fromkeys(top_images))
    return {"results": top_files[:n], "base_image_urls": urls, "qid": qid}


@app.post("/search/{qid}/")
async def get_feedback(qid: int, feedback: Dict[str, str] = None, eta: float = 0.05):
    embedders = EmbedderManager.instance().get_image_embedders()

    qman: QueryManager = QueryManager.instance()
    q: Query = qman.get_query(qid)

    losses = defaultdict(float)
    new_weights = []

    for embedder_name, embedder in embedders.items():
        embedder: ImageEmbedder
        for j, result in enumerate(q.get_embedder_result_by_name(embedder_name)):
            if result in feedback:
                if str(feedback[result]).strip().lower() not in ['true', 't', '1']:
                    losses[embedder_name] += 1 / (j + 1)

        new_weights.append((embedder_name, embedder.weight * (1.0 - eta * losses.get(embedder_name, 0.0))))

    weight_sum = sum([w for n, w in new_weights])
    new_weights = [(n, w / weight_sum) for n, w in new_weights]

    for embedder_name, weight in new_weights:
        embedder: ImageEmbedder = EmbedderManager.instance().get_image_embedder_by_name(embedder_name)
        embedder.weight = weight
        print(f"{embedder_name}={weight}")
    return {"successful": True}


@app.get("/image/{filename}")
async def download_image(filename: str):
    file_path = os.path.join(Configuration.instance().resources_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")
