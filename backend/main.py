import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymilvus import Collection

from core import embedder_manager, image_generator, query_manager
from core.query import Query
from models.models import SessionLocal, Directory, Image
from initialize import initialize
from models.schemas import AddDirectoryRequest, AddDirectoryResponse, HealthCheckResponse, DirectoryListResponse, \
    DirectoryModel, DirectoryDetailResponse, RemoveDirectoryResponse, RemoveDirectoryRequest, CreateQueryRequest, \
    CreateQueryResponse, GeneratorInfo, SearchLogsResponse, QueryLogEntry, \
    ServiceStatusResponse, ServiceLogResponse, SearchResponse, SearchRequest, UpdateDirectoryResponse, \
    UpdateDirectoryRequest
from indexing import image_indexing_service
from utils import aggregate_rankings, pil_image_to_base64

origins = ["http://localhost:3000", "http://127.0.0.1:3000", os.getenv("PUBLIC_IP", "http://127.0.0.1:3000")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield
    # directory_watcher.finalize()


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


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    return HealthCheckResponse(status="running")


@app.post("/directory", response_model=AddDirectoryResponse)
async def add_directory(request: AddDirectoryRequest):
    try:
        did = image_indexing_service.add_directory(request.path)
        return AddDirectoryResponse(status="directory added", id=did)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/directory", response_model=DirectoryListResponse)
async def get_directories():
    with SessionLocal() as session:
        directories = session.query(Directory).all()
        directory_models = [
            DirectoryModel(id=d.id, path=d.path, is_indexed=d.is_indexed, is_enabled=d.is_enabled)
            for d in directories
        ]
    return DirectoryListResponse(directories=directory_models)


@app.get("/directory/{did}", response_model=DirectoryDetailResponse)
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
                indexed_images_count = session.query(Image).filter_by(
                    directory_id=directory.id, is_indexed=True
                ).count()
                ratio = indexed_images_count / total_images
            else:
                ratio = 0.0
        else:
            ratio = 1.0

        directory_model = DirectoryModel(
            id=directory.id,
            path=directory.path,
            is_indexed=directory.is_indexed,
            is_enabled=directory.is_enabled
        )

    return DirectoryDetailResponse(
        directory=directory_model,
        images=image_paths,
        indexing_ratio=ratio
    )


@app.put("/directory/{did}", response_model=UpdateDirectoryResponse)
async def update_directory(did: int, request: UpdateDirectoryRequest):
    with SessionLocal() as session:
        directory = session.query(Directory).filter_by(id=did).first()
        if not directory:
            raise HTTPException(status_code=404, detail="Directory not found")

        # Update only the is_enabled field
        directory.is_enabled = request.is_enabled

        session.commit()

        updated_directory = DirectoryModel(
            id=directory.id,
            path=directory.path,
            is_indexed=directory.is_indexed,
            is_enabled=directory.is_enabled
        )

    return UpdateDirectoryResponse(
        status="Directory updated successfully",
        directory=updated_directory
    )


@app.delete("/directory", response_model=RemoveDirectoryResponse)
async def remove_directory(request: RemoveDirectoryRequest):
    image_indexing_service.remove_directory(request.path)
    return RemoveDirectoryResponse(status="Directory removed successfully.")


@app.post("/query", response_model=CreateQueryResponse)
async def create_query(request: CreateQueryRequest):
    query_object = Query(request.q)
    qid = query_manager.add_query(query_object)
    return CreateQueryResponse(qid=qid)


@app.post("/search", response_model=SearchResponse)
async def search(
        request: SearchRequest,
        request_obj: Request = None
):
    query_object = query_manager.get_query(request.qid)
    if not query_object:
        raise HTTPException(status_code=404, detail="Query not found")

    query = query_object.query
    generated_images = []

    if not query_object.generated_images:
        # Add the query text to each engine config
        generation_request = request.generation_config.model_dump()
        for engine in generation_request["engines"]:
            engine["prompt"] = query

        generated_images.extend(image_generator.generate(generation_request))
        query_object.generated_images.extend(generated_images)
    else:
        generated_images = query_object.generated_images

    embedders = embedder_manager.get_image_embedders()

    with SessionLocal() as session:
        indexed_directories = session.query(Directory.id).filter(
            Directory.is_indexed == True, Directory.is_enabled == True).all()

    indexed_directory_ids = [d[0] for d in indexed_directories]
    if not indexed_directory_ids:
        return SearchResponse(
            results=[],
            qid=request.qid,
            base_images=[pil_image_to_base64(image) for image in
                         generated_images] if request.include_base_images_in_preview else None,
            preview_url=str(request_obj.url_for("gallery", qid=request.qid))
        )

    # Create an expression for Milvus search
    directory_expr = f"directory_id in {indexed_directory_ids}"

    results = {}
    ranking_weights = []
    for embedder_name, embedder in embedders.items():
        collection_name = f"{embedder_name}"
        collection = Collection(name=collection_name)
        collection.load()

        for i, (image, engine_name) in enumerate(generated_images):
            query_embedding = embedder.embed(image)

            search_params = {
                "metric_type": "COSINE"
            }

            search_results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=request.num_images_to_retrieve,
                expr=directory_expr
            )

            results[f"{embedder_name}_{i}"] = [hit.id for hit in search_results[0]]

        rankings = [ranking for e, ranking in results.items() if e.startswith(embedder_name)]
        embedder_top_results = aggregate_rankings(rankings, weights=[1] * len(generated_images),
                                                  k=request.num_images_to_retrieve)
        query_object.add_embedder_results(embedder_name=embedder_name, results=embedder_top_results)

        for r in rankings:
            ranking_weights.append((r, embedder.weight))

    top_images = aggregate_rankings(
        rankers_results=[r for r, w in ranking_weights],
        weights=[w for r, w in ranking_weights],
        k=request.num_images_to_retrieve
    )

    query_object.final_results = top_images

    return SearchResponse(
        results=top_images,
        qid=request.qid,
        preview_url=str(request_obj.url_for("gallery", qid=request.qid)),
        base_images=[pil_image_to_base64(image) for image in
                     generated_images] if request.include_base_images_in_preview else None,
        verbose_results=query.embedder_results if request.verbose else None
    )


@app.get("/file")
async def get_file(file_path: str):
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        return FileResponse(file_path, media_type="application/octet-stream", filename=os.path.basename(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")


@app.get("/generator", response_model=List[GeneratorInfo])
async def get_generators():
    return image_generator.get_available_engines()


@app.get("/search/logs", response_model=SearchLogsResponse)
async def get_search_logs():
    queries = query_manager.list_queries()
    query_logs = [
        QueryLogEntry(qid=qid, query=qstr)
        for qid, qstr in queries
    ]
    return SearchLogsResponse(queries=query_logs)


@app.get("/service/status", response_model=ServiceStatusResponse)
async def service_status():
    return ServiceStatusResponse(status="running")


@app.get("/service/log", response_model=ServiceLogResponse)
async def service_log():
    return ServiceLogResponse(log="Service log not implemented yet.")


from routes.gallery import router as gallery_router

app.include_router(gallery_router)
