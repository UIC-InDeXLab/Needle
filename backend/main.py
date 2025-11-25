import os
import time

from collections import defaultdict
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
    UpdateDirectoryRequest, GeneratePoolRequest, GeneratePoolResponse, GuideImageData, EmbeddingData, \
    ComputeEmbeddingsRequest, ComputeEmbeddingsResponse, ImageEmbeddingsResponse
from indexing import image_indexing_service
from utils import aggregate_rankings, pil_image_to_base64, Timer
from version import VERSION as BACKEND_VERSION

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


@app.get("/version")
async def get_version():
    return {"version": BACKEND_VERSION}


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
        directory_models = []
        for d in directories:
            # Calculate indexing progress
            images = session.query(Image).filter_by(directory_id=d.id).all()
            if not d.is_indexed and len(images) > 0:
                indexed_images_count = session.query(Image).filter_by(
                    directory_id=d.id, is_indexed=True
                ).count()
                indexing_ratio = indexed_images_count / len(images)
            else:
                indexing_ratio = 1.0 if d.is_indexed else 0.0
            
            directory_models.append(DirectoryModel(
                id=d.id, 
                path=d.path, 
                is_indexed=d.is_indexed, 
                is_enabled=d.is_enabled,
                indexing_ratio=indexing_ratio
            ))
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
    timings = {}
    total_timer_start = time.perf_counter()
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

        with Timer("image_generation", timings):
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
            base_images=[pil_image_to_base64(image) for image, _ in
                         generated_images] if request.include_base_images_in_preview else None,
            preview_url=str(request_obj.url_for("gallery", qid=request.qid))
        )

    # Create an expression for Milvus search
    directory_expr = f"directory_id in {indexed_directory_ids}"

    results = {}
    ranking_weights = []
    verbose = {}
    for embedder_name, embedder in embedders.items():
        collection_name = f"{embedder_name}"
        collection = Collection(name=collection_name)
        collection.load()
        verbose[embedder_name] = defaultdict(list)

        for i, (image, engine_name) in enumerate(generated_images):
            with Timer(f"embedding_{embedder_name}", timings, aggregate=True):
                query_embedding = embedder.embed(image)

            search_params = {
                "metric_type": "COSINE"
            }

            with Timer(f"retrieval_{embedder_name}", timings, aggregate=True):
                search_results = collection.search(
                    data=[query_embedding],
                    anns_field="embedding",
                    param=search_params,
                    limit=request.num_images_to_retrieve,
                    expr=directory_expr
                )

            results[f"{embedder_name}_{i}"] = [hit.id for hit in search_results[0]]

            verbose[embedder_name][engine_name].append([hit.id for hit in search_results[0]])

        rankings = [ranking for e, ranking in results.items() if e.startswith(embedder_name)]
        embedder_top_results = aggregate_rankings(rankings, weights=[1] * len(generated_images),
                                                  k=request.num_images_to_retrieve)
        query_object.add_embedder_results(embedder_name=embedder_name, results=embedder_top_results)

        for r in rankings:
            ranking_weights.append((r, embedder.weight, embedder_name))

    with Timer("ranking_aggregation", timings):
        top_images = aggregate_rankings(
            rankers_results=[r for r, w, _ in ranking_weights],
            weights=[w for r, w, _ in ranking_weights],
            k=request.num_images_to_retrieve
        )

    query_object.final_results = top_images

    # Add total time and calculate the overhead
    timings["total_request_time"] = time.perf_counter() - total_timer_start

    return SearchResponse(
        results=top_images,
        qid=request.qid,
        preview_url=str(request_obj.url_for("gallery", qid=request.qid)),
        base_images=[pil_image_to_base64(image) for image, _ in
                     generated_images] if request.include_base_images_in_preview else None,
        verbose_results=verbose if request.verbose else None,
        timings=timings
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


@app.post("/variance-analysis/generate-pool", response_model=GeneratePoolResponse)
async def generate_pool(request: GeneratePoolRequest):
    """
    Generate a pool of guide images for variance analysis.
    This endpoint generates M_pool guide images and computes embeddings for all embedders.
    """
    # Prepare generation config - we need to generate pool_size images
    generation_request = request.generation_config.model_dump()
    for engine in generation_request["engines"]:
        engine["prompt"] = request.query
    
    # Adjust to generate the requested pool size
    # We'll use multiple engines if needed to reach pool_size
    original_num_images = generation_request.get("num_images", 1)
    original_num_engines = generation_request.get("num_engines_to_use", 1)
    
    # Calculate how many images per engine we need
    images_per_engine = max(1, request.pool_size // original_num_engines)
    generation_request["num_images"] = images_per_engine
    
    # Generate images
    generated_images = image_generator.generate(generation_request)
    
    # Limit to pool_size if we generated more
    generated_images = generated_images[:request.pool_size]
    
    # Get all embedders
    embedders = embedder_manager.get_image_embedders()
    embedder_names = list(embedders.keys())
    
    # Compute embeddings for all guide images using all embedders
    guide_images_data = []
    for idx, (image, engine_name) in enumerate(generated_images):
        embeddings_data = []
        for embedder_name, embedder in embedders.items():
            embedding = embedder.embed(image)
            embeddings_data.append(EmbeddingData(
                embedder_name=embedder_name,
                embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding
            ))
        
        guide_images_data.append(GuideImageData(
            image_index=idx,
            base64_image=pil_image_to_base64(image),
            embeddings=embeddings_data
        ))
    
    return GeneratePoolResponse(
        query=request.query,
        pool_size=len(guide_images_data),
        guide_images=guide_images_data,
        embedder_names=embedder_names
    )


@app.post("/variance-analysis/compute-embeddings", response_model=ComputeEmbeddingsResponse)
async def compute_embeddings(request: ComputeEmbeddingsRequest):
    """
    Compute embeddings for a list of images from file paths.
    Returns embeddings for all available embedders.
    """
    from PIL import Image as PImage
    
    embedders = embedder_manager.get_image_embedders()
    embedder_names = list(embedders.keys())
    
    results = []
    
    for image_path in request.image_paths:
        if not os.path.exists(image_path):
            from monitoring import logger
            logger.warning(f"Image path does not exist: {image_path}")
            continue
        
        try:
            # Load image
            img = PImage.open(image_path).convert("RGB")
            
            # Compute embeddings for all embedders
            embeddings_data = []
            for embedder_name, embedder in embedders.items():
                try:
                    embedding = embedder.embed(img)
                    embeddings_data.append(EmbeddingData(
                        embedder_name=embedder_name,
                        embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding
                    ))
                except Exception as e:
                    from monitoring import logger
                    logger.error(f"Error computing embedding with {embedder_name} for {image_path}: {e}", exc_info=True)
            
            if embeddings_data:
                results.append(ImageEmbeddingsResponse(
                    image_path=image_path,
                    embeddings=embeddings_data
                ))
        except Exception as e:
            from monitoring import logger
            logger.error(f"Error processing image {image_path}: {e}", exc_info=True)
            continue
    
    return ComputeEmbeddingsResponse(
        results=results,
        embedder_names=embedder_names
    )


from routes.gallery import router as gallery_router

app.include_router(gallery_router)
