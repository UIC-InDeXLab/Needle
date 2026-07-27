#!/usr/bin/env bash
#
# Build the Needle backend into a self-contained binary and place it where the
# Tauri bundler expects the sidecar. Also copies the runtime config files into
# the Tauri `resources/` folder so the packaged app is fully self-contained.
#
# Usage:  ./scripts/build-sidecar.sh
# Requires: python3, rustc (for the target triple), and network access for pip.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_TAURI="$(cd "$HERE/.." && pwd)"
ROOT="$(cd "$SRC_TAURI/../.." && pwd)"
BACKEND="$ROOT/backend"

BUILD_DIR="$SRC_TAURI/.sidecar-build"
RES_DIR="$SRC_TAURI/resources"
BACKEND_DIST="$RES_DIR/backend"
# Clean any previous onedir build so stale files don't linger.
rm -rf "$BACKEND_DIST"
mkdir -p "$RES_DIR"

echo ">> Creating build virtualenv"
python3 -m venv "$BUILD_DIR/venv"
# shellcheck disable=SC1091
source "$BUILD_DIR/venv/bin/activate"
python -m pip install --upgrade pip wheel

# PyTorch acceleration: CPU by default (smaller, portable); CUDA is opt-in.
# Controlled via NEEDLE_ACCEL=cpu|cuda (default: cpu).
# torch and torchvision MUST come from the same index/version or torchvision's
# compiled ops (e.g. torchvision::nms) fail to register at runtime.
NEEDLE_ACCEL="${NEEDLE_ACCEL:-cpu}"
OS_NAME="$(uname -s)"
if [ "$OS_NAME" = "Darwin" ]; then
  # macOS has no CUDA; the default wheel is MPS-enabled (Apple Silicon).
  echo ">> Installing macOS PyTorch + torchvision (MPS-enabled)"
  python -m pip install torch torchvision
elif [ "$NEEDLE_ACCEL" = "cuda" ]; then
  echo ">> Installing CUDA build of PyTorch + torchvision (NEEDLE_ACCEL=cuda)"
  python -m pip install torch torchvision
else
  echo ">> Installing CPU-only build of PyTorch + torchvision (NEEDLE_ACCEL=cpu)"
  python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

# Install the remaining requirements (torch/torchvision already satisfied) + PyInstaller.
python -m pip install -r "$BACKEND/requirements.txt" pyinstaller

# Data separator differs by platform (':' on unix, ';' on windows).
SEP=":"

echo ">> Building backend (PyInstaller onedir; unpacked at install time, not at launch)"
pyinstaller \
  --noconfirm --clean --onedir \
  --name needle-backend \
  --distpath "$BACKEND_DIST" \
  --workpath "$BUILD_DIR/work" \
  --specpath "$BUILD_DIR" \
  --paths "$BACKEND" \
  --add-data "$BACKEND/static${SEP}static" \
  --add-data "$BACKEND/templates${SEP}templates" \
  --collect-all uvicorn \
  --collect-all fastapi \
  --collect-all lancedb \
  --collect-all pyarrow \
  --collect-all torch \
  --collect-all torchvision \
  --collect-all timm \
  --collect-all diffusers \
  --collect-all transformers \
  --collect-all safetensors \
  --collect-all huggingface_hub \
  --collect-all packaging \
  --collect-submodules sqlalchemy \
  --hidden-import PIL._tkinter_finder \
  --copy-metadata torch \
  --copy-metadata torchvision \
  --copy-metadata diffusers \
  --copy-metadata transformers \
  --copy-metadata tokenizers \
  --copy-metadata accelerate \
  --copy-metadata safetensors \
  --copy-metadata huggingface-hub \
  --copy-metadata packaging \
  --copy-metadata requests \
  --copy-metadata filelock \
  --copy-metadata numpy \
  --copy-metadata pyyaml \
  --copy-metadata regex \
  --copy-metadata tqdm \
  --copy-metadata pillow \
  "$BACKEND/run_backend.py"

echo ">> Copying runtime config into Tauri resources"
cp "$ROOT/configs/embedders.json" "$RES_DIR/"
cp "$ROOT/configs/"*.env "$RES_DIR/" 2>/dev/null || true

# Align runtime CUDA flag with the build's acceleration choice.
if [ "$NEEDLE_ACCEL" = "cuda" ]; then
  echo "SERVICE__USE_CUDA=true" > "$RES_DIR/service.env"
else
  echo "SERVICE__USE_CUDA=false" > "$RES_DIR/service.env"
fi

echo ">> Done ($NEEDLE_ACCEL build). Backend dir: $BACKEND_DIST/needle-backend"
