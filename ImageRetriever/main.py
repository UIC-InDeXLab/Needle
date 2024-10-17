import asyncio
import base64
import io
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Dict, List

import numpy as np
import fastapi
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect


from initialize import initialize_embeddings, hnsw_indices
from logger import logger
from models import EmbedderManager, TileManager, Configuration
from models.embedders import ImageEmbedder
from models.generators import EngineManager
from models.query import QueryManager, Query
from utils import aggregate_rankings

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


@app.post("/query")
async def create_query(q: str):
    query_object = Query(q)
    qman: QueryManager = QueryManager.instance()
    qid = qman.add_query(query_object)
    return {"qid": qid}



@app.get("/search/{qid}")
async def search(qid: int, n: int = 20, k: int = 4, image_size: int = 512,
                 generator_engines: List[str] = fastapi.Query(None)):
    qman: QueryManager = QueryManager.instance()
    query_object = qman.get_query(qid)
    query = query_object.query

    generated_images = []

    if not query_object.generated_images:
        def generate_from_engine(engine_name: str):
            active_engine = EngineManager.instance().get_engine_by_name(engine_name)
            return active_engine.generate(prompt=query.strip(), image_size=image_size, k=k)

        tasks = [asyncio.to_thread(generate_from_engine, engine_name) for engine_name in generator_engines]
        results = await asyncio.gather(*tasks)

        for result in results:
            generated_images.extend(result)

        query_object.generated_images.extend(generated_images)
    else:
        generated_images = query_object.generated_images

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
    return {"results": top_files[:n],
            "qid": qid,
            "base_images": [base64.b64encode(image).decode('utf-8') for image in generated_images]
            }


@app.websocket("/feedback/{qid}")
async def guide_image_feedback(websocket: WebSocket, qid: int):
    await websocket.accept()

    qman: QueryManager = QueryManager.instance()

    try:
        data = await websocket.receive_json()
        query_obj = qman.get_query(qid)
        k = data.get("k", 4)
        image_size = data.get("image_size", 512)
        generator_engine = data.get("generator_engine", "runwayml")
        logger.info(f"k={k} image_size={image_size} generator_engine={generator_engine}")
        active_engine = EngineManager.instance().get_engine_by_name(generator_engine)

        if not query_obj.generated_images:
            generated_images = active_engine.generate(prompt=query_obj.query.strip(), image_size=image_size, k=k)
        else:
            generated_images = query_obj.generated_images

        base64_images = [base64.b64encode(image).decode('utf-8') for image in generated_images]

        await websocket.send_json({"generated_images": base64_images})
        rejected_count = 1

        while rejected_count > 0:
            feedback = await websocket.receive_json()
            approved_images = feedback.get("approved", [])
            query_obj.generated_images.extend([base64.b64decode(base64_image) for base64_image in approved_images])

            rejected_count = len(feedback.get("rejected", []))

            if rejected_count > 0:
                regenerated_images = active_engine.generate(prompt=query_obj.query.strip(), image_size=image_size,
                                                            k=rejected_count)
                base64_regenerated_images = [base64.b64encode(image).decode('utf-8') for image in regenerated_images]
                await websocket.send_json({"regenerated_images": base64_regenerated_images})
            else:
                break

        await websocket.send_json({"status": "all_approved"})

    except WebSocketDisconnect:
        await websocket.close()


@app.post("/search/{qid}/")
async def post_search_feedback(qid: int, feedback: Dict[str, str] = None, eta: float = 0.05):
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
        logger.info(f"{embedder_name}={weight}")
    return {"successful": True}


@app.get("/image/{filename}")
async def download_image(filename: str):
    file_path = os.path.join(Configuration.instance().resources_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")
