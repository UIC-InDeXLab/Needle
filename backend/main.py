import os
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Dict, List

import fastapi
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pymilvus import Collection

from core import embedder_manager, image_generator, query_manager
from core.embedders import ImageEmbedder
from core.query import Query
from database import SessionLocal, Directory, Image
from initialize import initialize
from monitoring import directory_watcher, logger
from settings import settings
from utils import aggregate_rankings, pil_image_to_base64

origins = ["http://localhost:3000", "http://127.0.0.1:3000", os.getenv("PUBLIC_IP", "http://127.0.0.1:3000")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield
    directory_watcher.finalize()
    embedder_manager.finalize()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/directory")
async def add_directory(path: str = Body(..., embed=True)):
    try:
        did = directory_watcher.add_directory(path)
        return {"status": "Directory added successfully.", "id": did}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/directory")
async def get_directories():
    with SessionLocal() as session:
        directories = session.query(Directory).all()
    return {"directories": directories}


@app.get("/directory/{did}")
async def get_directory(did: int):
    with SessionLocal() as session:
        directory = session.query(Directory).filter_by(id=did).first()
        if not directory:
            raise HTTPException(status_code=404, detail="Directory not found")

        images = session.query(Image).filter_by(directory_id=directory.id).all()
        image_paths = [img.path for img in images]

        if not directory.is_indexed:
            total_images = len(images)
            if total_images > 0:
                indexed_images_count = session.query(Image).filter_by(directory_id=directory.id,
                                                                      is_indexed=True).count()
                ratio = indexed_images_count / total_images
            else:
                ratio = 0.0
        else:
            ratio = 1.0

    return {
        "directory": {
            "id": directory.id,
            "path": directory.path,
            "is_indexed": directory.is_indexed
        },
        "images": image_paths,
        "indexing_ratio": ratio
    }


@app.delete("/directory")
async def remove_directory(path: str):
    directory_watcher.remove_directory(path)
    return {"status": "Directory removed successfully."}


@app.post("/query")
async def create_query(q: str = Body(..., embed=True)):
    query_object = Query(q)
    qid = query_manager.add_query(query_object)
    return {"qid": qid}


@app.get("/search/{qid}")
async def search(qid: int, n: int = 20, k: int = 1, image_size: int = 512,
                 generator_engines: List[str] = fastapi.Query(None),
                 include_base_images: bool = False
                 ):
    if generator_engines is None:
        generator_engines = [settings.generators.default_engine]

    query_object = query_manager.get_query(qid)
    query = query_object.query

    generated_images = []

    if not query_object.generated_images:
        generated_images.extend(image_generator.generate(query, generator_engines, k, image_size))
        query_object.generated_images.extend(generated_images)
    else:
        generated_images = query_object.generated_images

    embedders = embedder_manager.get_image_embedders()

    with SessionLocal() as session:
        indexed_directories = session.query(Directory.id).filter(Directory.is_indexed == True).all()

    indexed_directory_ids = [d[0] for d in indexed_directories]
    if not indexed_directory_ids:
        return {
            "results": [],
            "qid": qid,
            "base_images": [pil_image_to_base64(image) for image in generated_images]
        }

    # Create an expression for Milvus search
    directory_expr = f"directory_id in {indexed_directory_ids}"

    results = {}
    ranking_weights = []
    for embedder_name, embedder in embedders.items():
        collection_name = f"{embedder_name}"
        collection = Collection(name=collection_name)
        collection.load()

        for i, image in enumerate(generated_images):
            query_embedding = embedder.embed(image)

            search_params = {
                "metric_type": "COSINE"
            }

            search_results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=n,
                expr=directory_expr
            )

            results[f"{embedder_name}_{i}"] = [hit.id for hit in search_results[0]]

        rankings = [ranking for e, ranking in results.items() if e.startswith(embedder_name)]
        embedder_top_results = aggregate_rankings(rankings, weights=[1] * len(generated_images), k=n)
        query_object.add_embedder_results(embedder_name=embedder_name, results=embedder_top_results)

        for r in rankings:
            ranking_weights.append((r, embedder.weight))

    top_images = aggregate_rankings(
        rankers_results=[r for r, w in ranking_weights],
        weights=[w for r, w in ranking_weights],
        k=n
    )

    res = {"results": top_images,
           "qid": qid}

    if include_base_images:
        res["base_images"] = [pil_image_to_base64(image) for image in generated_images]

    return res


# @app.websocket("/feedback/{qid}")
# async def guide_image_feedback(websocket: WebSocket, qid: int):
#     await websocket.accept()
#
#     try:
#         data = await websocket.receive_json()
#         query_obj = query_manager.get_query(qid)
#         k = data.get("k", 4)
#         image_size = data.get("image_size", 512)
#         generator_engine = data.get("generator_engine", "runwayml")
#         logger.info(f"k={k} image_size={image_size} generator_engine={generator_engine}")
#         active_engine = engine_manager.get_engine_by_name(generator_engine)
#
#         if not query_obj.generated_images:
#             generated_images = active_engine.generate(prompt=query_obj.query.strip(), image_size=image_size, k=k)
#         else:
#             generated_images = query_obj.generated_images
#
#         base64_images = [base64.b64encode(image).decode('utf-8') for image in generated_images]
#
#         await websocket.send_json({"generated_images": base64_images})
#         rejected_count = 1
#
#         while rejected_count > 0:
#             feedback = await websocket.receive_json()
#             approved_images = feedback.get("approved", [])
#             query_obj.generated_images.extend([base64.b64decode(base64_image) for base64_image in approved_images])
#
#             rejected_count = len(feedback.get("rejected", []))
#
#             if rejected_count > 0:
#                 regenerated_images = active_engine.generate(prompt=query_obj.query.strip(), image_size=image_size,
#                                                             k=rejected_count)
#                 base64_regenerated_images = [base64.b64encode(image).decode('utf-8') for image in regenerated_images]
#                 await websocket.send_json({"regenerated_images": base64_regenerated_images})
#             else:
#                 break
#
#         await websocket.send_json({"status": "all_approved"})
#
#     except WebSocketDisconnect:
#         await websocket.close()


@app.post("/search/{qid}/")
async def post_search_feedback(qid: int, feedback: Dict[str, str] = None, eta: float = 0.05):
    embedders = embedder_manager.get_image_embedders()
    q: Query = query_manager.get_query(qid)

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
        embedder: ImageEmbedder = embedder_manager.get_image_embedder_by_name(embedder_name)
        embedder.weight = weight
        logger.info(f"{embedder_name}={weight}")
    return {"successful": True}

# @app.get("/image/{filename}")
# async def download_image(filename: str):
#     file_path = os.path.join(Configuration.instance().resources_dir, filename)
#     if os.path.exists(file_path):
#         return FileResponse(file_path)
#     else:
#         raise HTTPException(status_code=404, detail="File not found")
