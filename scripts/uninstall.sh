#!/bin/bash

# Needle Uninstallation — Docker-free.
#
# Removes the Needle desktop app and the `needlectl` CLI. Optionally removes the
# per-user data directory (~/.needle) containing the SQLite metadata, LanceDB
# vectors, saved credentials, and cached models.
#
# Usage: ./scripts/uninstall.sh [--purge]

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
print_status()  { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

echo -e "${RED}🗑️  Needle Uninstallation${NC}"
echo "========================="

PURGE=false
[[ "${1:-}" == "--purge" ]] && PURGE=true

if [[ "${OSTYPE:-}" == "darwin"* ]]; then OS="macos"; else OS="linux"; fi

# ---------------------------------------------------------------------------
# Remove the desktop application
# ---------------------------------------------------------------------------
print_status "Removing the desktop application..."
if [ "$OS" = "macos" ]; then
  if [ -d "/Applications/Needle.app" ]; then
    rm -rf "/Applications/Needle.app" && print_success "Removed /Applications/Needle.app"
  else
    print_warning "/Applications/Needle.app not found."
  fi
else
  # Debian package
  if command -v dpkg &>/dev/null && dpkg -l 2>/dev/null | grep -qiE '\bneedle\b'; then
    sudo apt-get remove -y needle 2>/dev/null || sudo dpkg -r needle 2>/dev/null || true
    print_success "Removed Needle .deb package."
  fi
  # AppImage
  if [ -f "$HOME/.local/bin/Needle.AppImage" ]; then
    rm -f "$HOME/.local/bin/Needle.AppImage" && print_success "Removed ~/.local/bin/Needle.AppImage"
  fi
fi

# ---------------------------------------------------------------------------
# Remove the CLI
# ---------------------------------------------------------------------------
print_status "Removing the needlectl CLI..."
for p in "/usr/local/bin/needlectl" "$HOME/.local/bin/needlectl"; do
  if [ -f "$p" ]; then
    rm -f "$p" 2>/dev/null || sudo rm -f "$p" 2>/dev/null || true
    [ ! -f "$p" ] && print_success "Removed $p"
  fi
done

# ---------------------------------------------------------------------------
# Optionally remove user data
# ---------------------------------------------------------------------------
DATA_DIR="$HOME/.needle"
if [ -d "$DATA_DIR" ]; then
  if [ "$PURGE" = true ]; then
    rm -rf "$DATA_DIR" && print_success "Removed user data at $DATA_DIR"
  else
    if [ -t 0 ]; then
      read -p "Remove indexed data and settings at $DATA_DIR? (y/N): " -n 1 -r; echo
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$DATA_DIR" && print_success "Removed $DATA_DIR"
      else
        print_status "Kept user data at $DATA_DIR (use --purge to remove)."
      fi
    else
      print_status "Kept user data at $DATA_DIR (run with --purge to remove)."
    fi
  fi
fi

echo ""
print_success "Uninstallation complete."
