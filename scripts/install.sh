#!/bin/bash

# Needle Installation (desktop app + CLI) — Docker-free.
#
# Builds the self-contained Needle desktop application (embedded SQLite +
# LanceDB, in-process image generation) and the `needlectl` CLI, then installs
# them. No Docker, PostgreSQL, or Milvus required.
#
# Usage: ./scripts/install.sh [fast|balanced|accurate]

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
print_status()  { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

echo -e "${GREEN}🪡 Needle Installation${NC}"
echo "======================="
echo "Self-contained desktop app + CLI (no Docker required)"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEEDLE_DIR="$(dirname "$SCRIPT_DIR")"
cd "$NEEDLE_DIR"
print_status "Needle directory: $NEEDLE_DIR"

# ---------------------------------------------------------------------------
# Configuration mode (controls which embedder set is used)
# ---------------------------------------------------------------------------
CONFIG_MODE="${1:-}"
if [ -z "$CONFIG_MODE" ]; then
  echo ""
  print_status "Choose your performance configuration:"
  echo "  1) Fast (default) - single model, fastest indexing/retrieval"
  echo "  2) Balanced       - 4 models, balanced accuracy"
  echo "  3) Accurate       - 6 models, best accuracy (slower)"
  echo ""
  read -p "Enter your choice (1-3) [default: 1]: " choice
  case "$choice" in
    2) CONFIG_MODE="balanced" ;;
    3) CONFIG_MODE="accurate" ;;
    *) CONFIG_MODE="fast" ;;
  esac
fi
case "$CONFIG_MODE" in
  fast|balanced|accurate) ;;
  *) print_error "Invalid config: $CONFIG_MODE (use fast|balanced|accurate)"; exit 1 ;;
esac
print_success "Selected '${CONFIG_MODE}' configuration"

# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------
if [[ "${OSTYPE:-}" == "darwin"* ]]; then
  OS="macos"; print_status "Detected macOS"
else
  OS="linux"; print_status "Detected Linux"
fi

# ---------------------------------------------------------------------------
# Dependency checks (no Docker!)
# ---------------------------------------------------------------------------
print_status "Checking build dependencies..."
missing=0
for tool in python3 node npm cargo rustc; do
  if ! command -v "$tool" &>/dev/null; then
    print_error "'$tool' not found."
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  echo ""
  print_error "Missing build tools. Install them and re-run:"
  echo "  - Python 3.12+   https://www.python.org"
  echo "  - Node.js 18+    https://nodejs.org"
  echo "  - Rust toolchain https://rustup.rs"
  exit 1
fi
print_success "All build tools present."

# ---------------------------------------------------------------------------
# Apply selected configuration
# ---------------------------------------------------------------------------
if [ -d "configs/${CONFIG_MODE}" ]; then
  print_status "Applying ${CONFIG_MODE} configuration..."
  cp -r "configs/${CONFIG_MODE}"/* "configs/"
  print_success "Configuration applied."
else
  print_warning "configs/${CONFIG_MODE} not found; using existing configs."
fi

# ---------------------------------------------------------------------------
# Build the desktop app (+ bundled backend sidecar)
# ---------------------------------------------------------------------------
print_status "Building the Needle desktop app (this can take a while)..."
chmod +x scripts/build-app.sh
./scripts/build-app.sh
print_success "Desktop app built."

BUNDLE_DIR="$NEEDLE_DIR/ui/src-tauri/target/release/bundle"

# ---------------------------------------------------------------------------
# Install the produced artifact
# ---------------------------------------------------------------------------
print_status "Installing the desktop app..."
if [ "$OS" = "macos" ]; then
  APP_PATH="$(find "$BUNDLE_DIR/macos" -maxdepth 1 -name '*.app' 2>/dev/null | head -1 || true)"
  if [ -n "$APP_PATH" ]; then
    cp -R "$APP_PATH" "/Applications/" && print_success "Installed to /Applications/$(basename "$APP_PATH")"
  else
    print_warning "No .app found. Open the .dmg in $BUNDLE_DIR/dmg to install manually."
  fi
else
  DEB_PATH="$(find "$BUNDLE_DIR/deb" -maxdepth 1 -name '*.deb' 2>/dev/null | head -1 || true)"
  APPIMAGE_PATH="$(find "$BUNDLE_DIR/appimage" -maxdepth 1 -name '*.AppImage' 2>/dev/null | head -1 || true)"
  if [ -n "$DEB_PATH" ] && command -v dpkg &>/dev/null; then
    sudo dpkg -i "$DEB_PATH" || sudo apt-get -f install -y
    print_success "Installed via dpkg: $(basename "$DEB_PATH")"
  elif [ -n "$APPIMAGE_PATH" ]; then
    mkdir -p "$HOME/.local/bin"
    cp "$APPIMAGE_PATH" "$HOME/.local/bin/Needle.AppImage"
    chmod +x "$HOME/.local/bin/Needle.AppImage"
    print_success "Installed AppImage to ~/.local/bin/Needle.AppImage"
    print_warning "Ensure ~/.local/bin is on your PATH."
  else
    print_warning "No installable artifact found in $BUNDLE_DIR. Check the build output."
  fi
fi

# ---------------------------------------------------------------------------
# Install the needlectl CLI
# ---------------------------------------------------------------------------
# The CLI is built alongside the backend by build-sidecar.sh and ships inside
# the app bundle, so there is nothing to compile here: it only has to be put on
# PATH. The packaged .deb/.rpm do this for you; this covers source installs.
print_status "Installing the needlectl CLI..."
CLI_BIN="ui/src-tauri/resources/bin/needlectl"
if [ -f "$CLI_BIN" ]; then
  if [ -w /usr/local/bin ]; then
    cp "$CLI_BIN" /usr/local/bin/needlectl
    chmod +x /usr/local/bin/needlectl
  elif sudo -n true 2>/dev/null; then
    sudo cp "$CLI_BIN" /usr/local/bin/needlectl
    sudo chmod +x /usr/local/bin/needlectl
  else
    mkdir -p "$HOME/.local/bin"
    cp "$CLI_BIN" "$HOME/.local/bin/needlectl"
    chmod +x "$HOME/.local/bin/needlectl"
    print_warning "Installed needlectl to ~/.local/bin (ensure it is on your PATH)."
  fi
  print_success "needlectl installed."
else
  print_warning "needlectl binary not found at $CLI_BIN; skipping CLI install."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
print_success "🎉 Installation complete!"
echo ""
echo "Launch Needle from your applications menu (or run the AppImage)."
echo "Your data lives in: ~/.needle/data (SQLite + LanceDB)."
echo ""
echo "CLI usage:"
echo "  needlectl directory add <path>   - index a folder"
echo "  needlectl query \"a red car\"      - search"
echo ""
print_status "Config mode: ${CONFIG_MODE}"
