#!/usr/bin/env bash
#
# Start the Needle Generator Service. Creates a local venv on first run.
#
#   ./run.sh                          # CPU or auto-detected GPU, all models
#   GEN_PORT=9000 ./run.sh            # custom port
#   GEN_MODEL=sdxl-turbo ./run.sh     # default model on startup
#   GEN_MODELS=sd-turbo,sdxl-turbo ./run.sh   # expose a subset of models
#
# For NVIDIA GPUs, install a CUDA build of torch inside the venv (see README).

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

if [ ! -d venv ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

exec python main.py
