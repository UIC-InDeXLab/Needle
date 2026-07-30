#!/usr/bin/env bash
#
# Build the Needle backend into a self-contained binary and place it where the
# Tauri bundler expects the sidecar. Also copies the runtime config files into
# the Tauri `resources/` folder so the packaged app is fully self-contained.
#
# Usage:  ./scripts/build-sidecar.sh
# Requires: python3, rustc (for the target triple), and network access for pip.
#
# Runs on Linux, macOS and Windows (Git Bash / MSYS).

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_TAURI="$(cd "$HERE/.." && pwd)"
ROOT="$(cd "$SRC_TAURI/../.." && pwd)"
BACKEND="$ROOT/backend"

# Platform differences: virtualenv layout, PyInstaller's --add-data separator
# and the executable suffix.
OS_NAME="$(uname -s)"
case "$OS_NAME" in
  MINGW*|MSYS*|CYGWIN*)
    VENV_BIN="Scripts"; SEP=";"; EXE_SUFFIX=".exe" ;;
  *)
    VENV_BIN="bin"; SEP=":"; EXE_SUFFIX="" ;;
esac

BUILD_DIR="$SRC_TAURI/.sidecar-build"
RES_DIR="$SRC_TAURI/resources"
BACKEND_DIST="$RES_DIR/backend"
# Clean any previous onedir build so stale files don't linger.
rm -rf "$BACKEND_DIST"
mkdir -p "$RES_DIR"

echo ">> Creating build virtualenv"
# Windows installs the interpreter as `python`; most Unix distros as `python3`.
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi
"$PYTHON_BIN" -m venv "$BUILD_DIR/venv"
# shellcheck disable=SC1091
source "$BUILD_DIR/venv/$VENV_BIN/activate"
python -m pip install --upgrade pip wheel

# PyTorch acceleration: CPU by default (smaller, portable); CUDA is opt-in.
# Controlled via NEEDLE_ACCEL=cpu|cuda (default: cpu).
# torch and torchvision MUST come from the same index/version or torchvision's
# compiled ops (e.g. torchvision::nms) fail to register at runtime.
NEEDLE_ACCEL="${NEEDLE_ACCEL:-cpu}"
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

# -- needlectl ---------------------------------------------------------------
# The CLI ships with the app so that installing Needle gives you both. It talks
# to the same backend and shares its settings, so the two stay in step.
echo ">> Building needlectl"
CLI_SRC="$ROOT/needlectl"
CLI_DIST="$RES_DIR/bin"
rm -rf "$CLI_DIST"
mkdir -p "$CLI_DIST"

python -m pip install -r "$CLI_SRC/requirements.txt" >/dev/null
pyinstaller \
  --noconfirm --clean --onefile \
  --name needlectl \
  --distpath "$CLI_DIST" \
  --workpath "$BUILD_DIR/cli-work" \
  --specpath "$BUILD_DIR" \
  --paths "$CLI_SRC" \
  --collect-submodules shellingham \
  "$CLI_SRC/needlectl.py"

if [ ! -f "$CLI_DIST/needlectl$EXE_SUFFIX" ]; then
  echo ">> ERROR: needlectl was not produced at $CLI_DIST/needlectl$EXE_SUFFIX" >&2
  exit 1
fi

echo ">> Done ($NEEDLE_ACCEL build)."
echo "   Backend: $BACKEND_DIST/needle-backend"
echo "   CLI:     $CLI_DIST/needlectl$EXE_SUFFIX"

# Fail loudly if the expected executable is missing: the Tauri shell resolves it
# by an exact path, so a silently renamed/missing binary would only surface as a
# blank app at runtime.
if [ ! -f "$BACKEND_DIST/needle-backend/needle-backend$EXE_SUFFIX" ]; then
  echo ">> ERROR: expected backend executable not found:" >&2
  echo "   $BACKEND_DIST/needle-backend/needle-backend$EXE_SUFFIX" >&2
  exit 1
fi
