import os
from contextlib import asynccontextmanager
from typing import List

import fastapi
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymilvus import Collection

from core import embedder_manager, image_generator, query_manager
from core.query import Query
from database import SessionLocal, Directory, Image
from initialize import initialize
from monitoring import directory_watcher
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

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/health")
async def health_check():
    # TODO: Perform any necessary health checks here, e.g. database ping.
    return {"status": "running"}


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
async def search(qid: int, n: int = settings.query.default_num_images_to_retrieve,
                 k: int = settings.query.default_num_images_to_generate,
                 image_size: int = settings.query.default_generated_image_size,
                 include_base_images_in_preview: bool = settings.query.include_base_images_in_preview,
                 generator_engines: List[str] = fastapi.Query(None),
                 request: Request = None
                 ):
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
            "base_images": [pil_image_to_base64(image) for image in generated_images],
            "preview_url": str(request.url_for("gallery", qid=qid))
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

    query_object.final_results = top_images

    res = {
        "results": top_images,
        "qid": qid,
        "preview_url": str(request.url_for("gallery", qid=qid))
    }

    if include_base_images_in_preview:
        res["base_images"] = [pil_image_to_base64(image) for image in generated_images]

    return res


@app.get("/file")
async def get_file(file_path: str):
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        return FileResponse(file_path, media_type="application/octet-stream", filename=os.path.basename(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")


@app.get("/generators")
async def get_generators():
    # Assume image_generator.list_engines() returns a list of available generator names
    return {"generators": image_generator.get_available_engines()}


@app.get("/generator/{name}")
async def describe_generator(name: str):
    # Assume image_generator.get_engine_details(name) returns details about a generator
    details = image_generator.get_engine_details(name)
    if not details:
        raise HTTPException(status_code=404, detail="Generator not found")
    return {"name": name, "details": details}


# Search logs endpoint
@app.get("/search/logs")
async def get_search_logs():
    # Assume query_manager.list_queries() returns [(qid, query_str), ...]
    queries = query_manager.list_queries()
    return {"queries": [{"qid": qid, "query": qstr} for qid, qstr in queries]}


# Service status/log endpoints
@app.get("/service/status")
async def service_status():
    # This could check docker or internal states. For now, return a dummy status.
    return {"status": "running"}


@app.get("/service/log")
async def service_log():
    # Return a simple log snippet or instructions
    # Real implementation might tail docker logs or read from a log file.
    return {"log": "Service log not implemented yet."}


from routes.gallery import router as gallery_router

app.include_router(gallery_router)
