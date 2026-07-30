import base64
import os
import re
import threading
import time

from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core import embedder_manager, image_generator, query_manager, setup_manager
from core.device import gpu_available, select_device
from core.generation.local_engine import (
    DEFAULT_MODEL as LOCAL_DEFAULT_MODEL,
    MODELS as LOCAL_MODELS,
    is_downloaded as is_model_downloaded,
)
from core.query import Query
from indexing.repositories.repositories import VectorRepository
from models.models import SessionLocal, Directory, Image
from models.schemas import AddDirectoryRequest, AddDirectoryResponse, HealthCheckResponse, DirectoryListResponse, \
    DirectoryModel, DirectoryDetailResponse, RemoveDirectoryResponse, RemoveDirectoryRequest, CreateQueryRequest, \
    CreateQueryResponse, GeneratorInfo, SearchLogsResponse, QueryLogEntry, \
    ServiceStatusResponse, ServiceLogResponse, SearchResponse, SearchRequest, UpdateDirectoryResponse, \
    UpdateDirectoryRequest, GeneratePoolRequest, GeneratePoolResponse, GuideImageData, EmbeddingData, \
    ComputeEmbeddingsRequest, ComputeEmbeddingsResponse, ImageEmbeddingsResponse, SetCredentialsRequest, \
    ConfigureSetupRequest, SetGpuRequest, GenerateImagesRequest, LoadModelRequest, SaveImageRequest
from indexing import image_indexing_service
from monitoring import logger
from settings import settings
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


@app.post("/setup/gpu")
async def setup_set_gpu(request: SetGpuRequest):
    """Turn GPU acceleration on/off after onboarding and reload models onto the
    new device. Weights are already cached, so this does not re-download."""
    try:
        return setup_manager.set_use_gpu(request.use_gpu)
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
# Declared sync on purpose: scanning a folder blocks, and FastAPI runs sync
# handlers in a threadpool so the event loop stays responsive.
def add_directory(request: AddDirectoryRequest):
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
# Declared sync on purpose. This runs image generation and embedding, which take
# seconds and hold the GIL; as an ``async def`` it would block the event loop and
# freeze every other request (status polling, directory listing, ...) until done.
# FastAPI runs sync handlers in a threadpool instead.
def search(
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
# Sync on purpose: generation blocks for seconds. See the note on /search.
def test_generator(name: str, request: SetCredentialsRequest):
    """Generate a single small test image with one engine. Also warms the model
    so the first real search is fast. Returns the image as a data URL + timing."""
    params = request.params or {}
    prompt = params.pop("prompt", None) or "a scenic landscape, high detail"

    # Testing must not silently pull several GB of weights: the caller asked for
    # a quick check, not a download. Downloading is an explicit action instead.
    engine = image_generator.local_engine()
    if name in (engine.name, *engine.aliases):
        model_id = params.get("model") or LOCAL_DEFAULT_MODEL
        if model_id in LOCAL_MODELS and not is_model_downloaded(model_id):
            raise HTTPException(
                status_code=409,
                detail=f"{LOCAL_MODELS[model_id]['label']} is not downloaded yet. "
                       "Download it first, then run the test.",
            )
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


# -- on-device generation ---------------------------------------------------

@app.get("/generate/models")
async def generate_models():
    """Catalog of on-device models, which are already downloaded, and the
    device generation would run on."""
    engine = image_generator.local_engine()
    return {
        # Whether this build *can* generate on-device. Downloaded weights are
        # reported per model below, so the page can offer a download.
        "available": engine.libraries_available(),
        "error": engine.import_error(),
        "device": engine.device(),
        "default_model": LOCAL_DEFAULT_MODEL,
        "loaded_model": engine.state().get("loaded_model"),
        "models": [engine.model_card(m) for m in LOCAL_MODELS],
    }


@app.get("/generate/state")
async def generate_state():
    """Current download/load/generation progress for the on-device engine."""
    return image_generator.local_engine().state()


@app.post("/generate/load")
async def generate_load(request: LoadModelRequest):
    """Download (if needed) and load a model in the background so the UI can
    show progress instead of blocking on the first generate call."""
    engine = image_generator.local_engine()
    if not engine.libraries_available():
        raise HTTPException(status_code=503, detail="On-device generation is not available in this build")

    # Report the requested model immediately. The worker thread has to import
    # diffusers before it can publish any progress, and during that window the
    # state would otherwise still read "idle" and the UI would conclude that
    # nothing is happening.
    state = engine.begin_load(request.model)
    if state is not None:
        threading.Thread(target=_load_model_quietly, args=(engine, request.model), daemon=True).start()
    return engine.state()


def _load_model_quietly(engine, model_id: str):
    try:
        engine.ensure_loaded(model_id)
    except Exception as exc:
        logger.error(f"Failed to load generation model '{model_id}': {exc}", exc_info=True)


@app.post("/generate/images")
async def generate_images(request: GenerateImagesRequest):
    """Generate images on-device and return them as data URLs."""
    engine = image_generator.local_engine()
    if not engine.libraries_available():
        raise HTTPException(status_code=503, detail="On-device generation is not available in this build")
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    # Weights are several GB, so never fetch them as a side effect of pressing
    # Generate: ask for an explicit download instead (the UI offers a button).
    model_id = request.model if request.model in LOCAL_MODELS else LOCAL_DEFAULT_MODEL
    if not is_model_downloaded(model_id):
        raise HTTPException(
            status_code=409,
            detail=f"{LOCAL_MODELS[model_id]['label']} is not downloaded yet. "
                   "Download it first, then generate.",
        )

    params = {
        "model": request.model,
        "width": request.width,
        "height": request.height,
        "steps": request.steps,
        "seed": request.seed,
    }
    try:
        images, meta = await run_in_threadpool(
            engine.generate_detailed, request.prompt, request.num_images, request.size, params
        )
    except Exception as e:
        logger.error(f"On-device generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "images": [pil_image_to_base64(im) for im in images],
        "prompt": request.prompt,
        **meta,
    }


@app.post("/generate/save")
async def generate_save(request: SaveImageRequest):
    """Write a generated image into a user-chosen folder."""
    directory = Path(request.directory).expanduser()
    if not directory.is_dir():
        raise HTTPException(status_code=400, detail="Destination folder does not exist")

    # Keep only the basename so a crafted filename can't escape the chosen
    # folder, and force the extension we actually write.
    stem = Path(request.filename or "needle").name
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem).lstrip(".") or "needle"
    stem = Path(stem).stem

    target = directory / f"{stem}.png"
    counter = 1
    while target.exists():
        target = directory / f"{stem}-{counter}.png"
        counter += 1

    payload = request.image.split(",", 1)[-1]
    try:
        target.write_bytes(base64.b64decode(payload))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save image: {e}")
    return {"path": str(target)}


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


# -- system information -----------------------------------------------------

_STARTED_AT = time.time()
_GITHUB_REPO = "UIC-InDeXLab/Needle"


def _dir_size(path) -> int:
    """Total bytes under ``path`` (0 when missing). Symlinks are not followed so
    a library folder linked into the data dir is never counted twice."""
    total = 0
    p = Path(path)
    if not p.exists():
        return 0
    if p.is_file():
        return p.stat().st_size
    for entry in p.rglob("*"):
        try:
            if entry.is_file() and not entry.is_symlink():
                total += entry.stat().st_size
        except OSError:
            continue
    return total


def _model_cache_size() -> int:
    """Bytes used by downloaded model weights in the shared Hugging Face cache."""
    try:
        from huggingface_hub import scan_cache_dir

        return int(scan_cache_dir().size_on_disk)
    except Exception:
        return 0


def _system_info() -> dict:
    import platform as _platform

    storage = settings.storage
    data_dir = Path(storage.data_dir)
    vectors = _dir_size(storage.lancedb_path)
    metadata = _dir_size(storage.sqlite_path)
    logs = _dir_size(data_dir / "logs")
    data_total = _dir_size(data_dir)
    models = _model_cache_size()

    with SessionLocal() as session:
        directories = session.query(Directory).count()
        images = session.query(Image).count()
        indexed_images = session.query(Image).filter(Image.is_indexed == True).count()  # noqa: E712

    try:
        import torch

        torch_version = torch.__version__
    except Exception:
        torch_version = None

    return {
        "version": BACKEND_VERSION,
        "repo": _GITHUB_REPO,
        "uptime_seconds": int(time.time() - _STARTED_AT),
        "platform": {
            "system": _platform.system(),
            "release": _platform.release(),
            "machine": _platform.machine(),
            "python": _platform.python_version(),
            "torch": torch_version,
            "device": str(select_device()),
            "gpu_available": gpu_available(),
        },
        "library": {
            "directories": directories,
            "images": images,
            "indexed_images": indexed_images,
            "embedders": [e for e in embedder_manager.get_image_embedders()],
        },
        "storage": {
            "data_dir": str(data_dir),
            "vectors_bytes": vectors,
            "metadata_bytes": metadata,
            "logs_bytes": logs,
            # Whatever else lives in the data dir (configs, credentials, caches).
            "other_bytes": max(data_total - vectors - metadata - logs, 0),
            "data_total_bytes": data_total,
            "models_bytes": models,
            "total_bytes": data_total + models,
        },
    }


@app.get("/system/info")
def system_info():
    """Version, platform, library counts and on-disk usage for the Status page.

    Sync so FastAPI runs it in a threadpool: walking the data directory and the
    model cache is blocking I/O.
    """
    return _system_info()


@app.get("/system/update")
def system_update():
    """Check GitHub for a newer release.

    Done server-side to avoid a cross-origin request from the webview, and only
    when the user asks: Needle never phones home on its own.
    """
    current = BACKEND_VERSION
    try:
        # The repository also tags needlectl releases (needlectl/vX.Y.Z), and
        # /releases/latest would happily return one of those, so list releases
        # and keep only the desktop app's own "vX.Y.Z" tags.
        resp = requests.get(
            f"https://api.github.com/repos/{_GITHUB_REPO}/releases",
            headers={"Accept": "application/vnd.github+json"},
            params={"per_page": 30},
            timeout=10,
        )
        resp.raise_for_status()
        releases = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach GitHub: {exc}")

    release = next(
        (
            r for r in releases
            if not r.get("draft") and not r.get("prerelease")
            and re.fullmatch(r"v\d+(\.\d+)*", str(r.get("tag_name") or ""))
        ),
        None,
    )
    if release is None:
        return {"current": current, "latest": None, "update_available": False,
                "message": "No desktop releases published yet."}

    latest = str(release.get("tag_name") or "").lstrip("v")
    return {
        "current": current,
        "latest": latest or None,
        "update_available": bool(latest) and _is_newer(latest, current),
        "url": release.get("html_url"),
        "published_at": release.get("published_at"),
        "notes": (release.get("body") or "")[:4000],
    }


def _parse_version(value: str):
    parts = re.findall(r"\d+", value or "")
    return tuple(int(p) for p in parts[:3]) or (0,)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


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
