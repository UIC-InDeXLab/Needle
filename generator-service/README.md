# Needle Generator

The optional **image-generation companion** for the Needle suite. Run it wherever
you have compute (a GPU box, another machine, or the same machine as Needle), and
connect the Needle desktop app to it. Keeping generation out of the app keeps
Needle itself lightweight — no model ships inside the app.

Needle discovers the models this service offers and lets you switch between them
per search.

## Run it

```bash
cd generator-service
./run.sh
```

This starts the service on `http://0.0.0.0:8001`. First run downloads the default
model (SD-Turbo, ~2 GB). Other models download the first time you select them.

Options (environment variables):

| Variable | Default | Meaning |
|---|---|---|
| `GEN_MODEL` | `sd-turbo` | default model id on startup |
| `GEN_MODELS` | *(all)* | comma-separated subset of models to expose |
| `GEN_HOST` | `0.0.0.0` | bind host |
| `GEN_PORT` | `8001` | bind port |

### Bundled models

| id | model | notes |
|---|---|---|
| `sd-turbo` | `stabilityai/sd-turbo` | fastest, 1 step, 384–512px |
| `sdxl-turbo` | `stabilityai/sdxl-turbo` | higher quality, 1–4 steps, up to 1024px |
| `flux-schnell` | `black-forest-labs/FLUX.1-schnell` | best quality, large, needs a capable GPU |

Only one model stays resident at a time; selecting a different model in Needle
swaps it in (and frees the previous one).

### NVIDIA GPU

For a big speed-up, install a CUDA build of PyTorch in the service's venv:

```bash
cd generator-service
python3 -m venv venv && source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu124   # match your CUDA
pip install -r requirements.txt
python main.py
```

The service auto-detects CUDA / Apple MPS / CPU.

## Connect it to the Needle app

In Needle, open **Generators**. Under **Needle suite**, Needle auto-detects a
service running locally at `http://127.0.0.1:8001`. Running it elsewhere? Enter
its URL (e.g. `http://192.168.1.10:8001`) and click **Connect**. Then pick a
model and it's used for search.

## API

- `GET /health` → `{status, service, device, model}`
- `GET /capabilities` → `{service, version, device, default_model, models: [{id, label, description, default_steps, sizes, default_size}]}`
- `GET /engines` → `[{name, description, required_params}]` (back-compat)
- `POST /generate` with `{prompt, num_images, model?, width?, height?, image_size?, steps?}` →
  `{"images": [{"base64_image": "<png b64>", "engine_name": "<model id>"}]}`
