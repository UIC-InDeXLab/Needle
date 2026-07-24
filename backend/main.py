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

from core import embedder_manager, image_generator, query_manager, setup_manager
from core.query import Query
from indexing.repositories.repositories import VectorRepository
from models.models import SessionLocal, Directory, Image
from models.schemas import AddDirectoryRequest, AddDirectoryResponse, HealthCheckResponse, DirectoryListResponse, \
    DirectoryModel, DirectoryDetailResponse, RemoveDirectoryResponse, RemoveDirectoryRequest, CreateQueryRequest, \
    CreateQueryResponse, GeneratorInfo, SearchLogsResponse, QueryLogEntry, \
    ServiceStatusResponse, ServiceLogResponse, SearchResponse, SearchRequest, UpdateDirectoryResponse, \
    UpdateDirectoryRequest, GeneratePoolRequest, GeneratePoolResponse, GuideImageData, EmbeddingData, \
    ComputeEmbeddingsRequest, ComputeEmbeddingsResponse, ImageEmbeddingsResponse, SetCredentialsRequest, \
    ConfigureSetupRequest
from indexing import image_indexing_service
from utils import aggregate_rankings, pil_image_to_base64, Timer
from version import VERSION as BACKEND_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Keep first launch lightweight: do not load any models here. The setup manager
    # only performs heavy initialization if the user has already completed onboarding.
    setup_manager.startup()
    yield
    # directory_watcher.finalize()


app = FastAPI(lifespan=lifespan)

# This backend only listens on localhost and is the private companion of the
# desktop app (whose webview origin is e.g. http://tauri.localhost) or the CLI.
# Allow any origin so the bundled UI can read responses; no credentials are used.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    return HealthCheckResponse(status="running")


@app.get("/setup/options")
async def setup_options():
    """Available profiles and whether a usable GPU is present (for onboarding)."""
    return setup_manager.options()


@app.get("/setup/status")
async def setup_status():
    """Current setup/initialization state (for the welcome screen + progress)."""
    return setup_manager.status()


@app.post("/setup/configure")
async def setup_configure(request: ConfigureSetupRequest):
    """Apply the chosen profile + GPU option and begin background initialization."""
    try:
        return setup_manager.configure(request.profile, request.use_gpu)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _require_ready():
    if not setup_manager.is_ready():
        status = setup_manager.status()
        detail = "Needle is not ready yet. Complete setup first." if not status["configured"] \
            else f"Needle is initializing ({status['state']}). Please wait."
        raise HTTPException(status_code=503, detail=detail)


@app.get("/version")
async def get_version():
    return {"version": BACKEND_VERSION}


@app.post("/directory", response_model=AddDirectoryResponse)
async def add_directory(request: AddDirectoryRequest):
    _require_ready()
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
    _require_ready()
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
        generation_request["prompt"] = query
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

    # Restrict search to indexed & enabled directories
    directory_ids = indexed_directory_ids

    results = {}
    ranking_weights = []
    verbose = {}
    vector_repo = VectorRepository()
    for embedder_name, embedder in embedders.items():
        verbose[embedder_name] = defaultdict(list)

        for i, (image, engine_name) in enumerate(generated_images):
            with Timer(f"embedding_{embedder_name}", timings, aggregate=True):
                query_embedding = embedder.embed(image)

            with Timer(f"retrieval_{embedder_name}", timings, aggregate=True):
                hit_paths = vector_repo.search(
                    embedder_name,
                    query_embedding,
                    limit=request.num_images_to_retrieve,
                    directory_ids=directory_ids,
                )

            results[f"{embedder_name}_{i}"] = hit_paths

            verbose[embedder_name][engine_name].append(hit_paths)

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


@app.post("/generator/{name}/credentials")
async def set_generator_credentials(name: str, request: SetCredentialsRequest):
    try:
        image_generator.set_credentials(name, request.params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "credentials saved", "engine": name}


@app.get("/generator/{name}/capabilities")
async def get_generator_capabilities(name: str, base_url: str | None = None):
    """Proxy the connected companion service's ``/capabilities`` (avoids browser
    CORS by fetching server-side). Returns {} when the service is unreachable."""
    params = {"base_url": base_url} if base_url else {}
    try:
        return image_generator.get_capabilities(name, params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/generator/{name}/test")
async def test_generator(name: str, request: SetCredentialsRequest):
    """Generate a single small test image with one engine. Also warms the model
    so the first real search is fast. Returns the image as a data URL + timing."""
    params = request.params or {}
    prompt = params.pop("prompt", None) or "a scenic landscape, high detail"
    gen_config = {
        "engines": [{"name": name, "params": params, "prompt": prompt}],
        "num_images": 1,
        "image_size": "SMALL",
        "num_engines_to_use": 1,
        "use_fallback": False,
        "prompt": prompt,
    }
    started = time.perf_counter()
    try:
        images = image_generator.generate(gen_config)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    if not images:
        raise HTTPException(status_code=502, detail="Engine returned no image")
    image, engine_name = images[0]
    return {
        "engine": engine_name,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "image": pil_image_to_base64(image),
    }


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
