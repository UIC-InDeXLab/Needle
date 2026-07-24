#!/usr/bin/env bash
#
# Build the Needle desktop application (and its bundled backend) into native
# installers for the current platform:
#   - Linux : .AppImage and .deb
#   - macOS : .dmg and .app
#
# Output: ui/src-tauri/target/release/bundle/
#
# Requirements: node + npm, rustc + cargo, python3 (with network access for pip).

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UI="$ROOT/ui"
SRC_TAURI="$UI/src-tauri"
LOGO="$UI/src/assets/images/logo.png"

require() {
  if ! command -v "$1" &>/dev/null; then
    err "'$1' is required but not installed. $2"
    exit 1
  fi
}

echo -e "${GREEN}🪡 Building Needle desktop app${NC}"
echo "==============================="

info "Checking build tools..."
require node   "Install Node.js 18+ (https://nodejs.org)."
require npm    "Install npm (bundled with Node.js)."
require cargo  "Install Rust (https://rustup.rs)."
require rustc  "Install Rust (https://rustup.rs)."
require python3 "Install Python 3.12+."
ok "Build tools present."

cd "$UI"

info "Installing frontend dependencies..."
npm install

# Generate application icons from the logo if they don't exist yet.
if [ ! -f "$SRC_TAURI/icons/icon.icns" ] && [ ! -f "$SRC_TAURI/icons/128x128.png" ]; then
  if [ -f "$LOGO" ]; then
    info "Generating application icons from $LOGO ..."
    npx tauri icon "$LOGO"
    ok "Icons generated."
  else
    warn "Logo not found at $LOGO; Tauri will use its default icon."
  fi
fi

# Choose PyTorch acceleration: CPU by default; offer CUDA when an NVIDIA GPU is present.
if [ -z "${NEEDLE_ACCEL:-}" ]; then
  NEEDLE_ACCEL="cpu"
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
    if [ -t 0 ]; then
      warn "NVIDIA GPU detected: ${GPU_NAME:-unknown}"
      read -r -p "Enable CUDA acceleration? (larger build, much faster) [y/N]: " ans
      case "$ans" in [Yy]*) NEEDLE_ACCEL="cuda" ;; esac
    else
      info "NVIDIA GPU detected (${GPU_NAME:-unknown}); defaulting to CPU. Set NEEDLE_ACCEL=cuda to enable CUDA."
    fi
  fi
fi
export NEEDLE_ACCEL
info "PyTorch acceleration: $NEEDLE_ACCEL"

info "Building the backend sidecar (PyInstaller). This can take a while..."
bash "$SRC_TAURI/scripts/build-sidecar.sh"
ok "Backend sidecar built."

info "Building the desktop app + installers (tauri build)..."
npm run tauri:build

BUNDLE_DIR="$SRC_TAURI/target/release/bundle"
ok "Build complete."
echo ""
echo "Installers are in: $BUNDLE_DIR"
find "$BUNDLE_DIR" -maxdepth 2 -type f \( -name "*.AppImage" -o -name "*.deb" -o -name "*.dmg" \) 2>/dev/null || true
