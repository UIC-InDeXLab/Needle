#!/bin/bash

# Needle Uninstallation Script
# Removes Needle installation from ~/.needle
# Usage: curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/uninstall.sh | bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${RED}🗑️  Needle Uninstallation${NC}"
echo "============================="
echo "This will remove Needle from ~/.needle"
echo ""

# Only target ~/.needle installation
NEEDLE_DIR="$HOME/.needle"

if [ ! -d "$NEEDLE_DIR" ]; then
    print_error "Needle installation not found at $NEEDLE_DIR"
    print_status "Nothing to uninstall."
    exit 0
fi

print_status "Found Needle installation at: $NEEDLE_DIR"

# Confirm uninstallation - handle both interactive and non-interactive modes
if [ -t 0 ]; then
    # Interactive mode
    read -p "Are you sure you want to uninstall Needle? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Uninstallation cancelled."
        exit 0
    fi
else
    # Non-interactive mode (piped from curl)
    print_warning "Running in non-interactive mode. Proceeding with uninstallation..."
    print_status "To cancel, press Ctrl+C within 5 seconds..."
    sleep 5
fi

### Step 1: Stop all services using needlectl
print_status "Stopping all services..."

if command -v needlectl &> /dev/null; then
    needlectl service stop 2>/dev/null || true
else
    # Manual stop if needlectl not available
    # Stop backend
    if [ -f "$NEEDLE_DIR/logs/backend.pid" ]; then
        BACKEND_PID=$(cat "$NEEDLE_DIR/logs/backend.pid")
        if kill -0 $BACKEND_PID 2>/dev/null; then
            kill $BACKEND_PID 2>/dev/null || true
            print_success "Backend stopped"
        fi
    fi

    # Stop image-generator-hub
    if [ -f "$NEEDLE_DIR/logs/image-generator-hub.pid" ]; then
        IMG_GEN_PID=$(cat "$NEEDLE_DIR/logs/image-generator-hub.pid")
        if kill -0 $IMG_GEN_PID 2>/dev/null; then
            kill $IMG_GEN_PID 2>/dev/null || true
            print_success "Image-generator-hub stopped"
        fi
    fi

    # Stop Docker infrastructure
    if [ -f "$NEEDLE_DIR/docker/docker-compose.infrastructure.yaml" ]; then
        docker compose -f "$NEEDLE_DIR/docker/docker-compose.infrastructure.yaml" down 2>/dev/null || true
    fi
fi

print_success "Services stopped"

### Step 2: Remove needlectl binary
print_status "Removing needlectl binary..."

if [ -f "/usr/local/bin/needlectl" ]; then
    sudo rm -f /usr/local/bin/needlectl 2>/dev/null || rm -f /usr/local/bin/needlectl 2>/dev/null || true
    if [ ! -f "/usr/local/bin/needlectl" ]; then
        print_success "needlectl removed from /usr/local/bin"
    else
        print_warning "Could not remove /usr/local/bin/needlectl (may need sudo)"
    fi
fi

if [ -f "$HOME/.local/bin/needlectl" ]; then
    rm -f "$HOME/.local/bin/needlectl"
    print_success "needlectl removed from ~/.local/bin"
fi

### Step 3: Handle optional Docker volume removal
REMOVE_DOCKER_VOLUMES=false

if [ -t 0 ]; then
    # Interactive mode - ask user
    echo ""
    print_warning "Docker volumes may contain indexed data and images"
    read -p "Do you want to remove Docker volumes? This will delete all indexed data. (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && REMOVE_DOCKER_VOLUMES=true
fi

if [ "$REMOVE_DOCKER_VOLUMES" = true ]; then
    print_status "Removing Docker volumes..."
    docker volume prune -f 2>/dev/null || true
    print_success "Docker volumes cleaned up"
fi

### Step 4: Remove entire Needle directory
print_status "Removing Needle installation directory..."

# Clean up Docker volume files (may have root ownership)
if [ -d "$NEEDLE_DIR/volumes" ]; then
    print_status "Cleaning up Docker volume files..."
    docker run --rm -v "$NEEDLE_DIR/volumes:/volumes" alpine sh -c "rm -rf /volumes/*" 2>/dev/null || true
fi

rm -rf "$NEEDLE_DIR" 2>/dev/null || {
    print_error "Failed to remove some files in $NEEDLE_DIR"
    print_status "You may need to run: sudo rm -rf $NEEDLE_DIR"
}

if [ ! -d "$NEEDLE_DIR" ]; then
    print_success "Needle directory removed"
else
    print_warning "Some files could not be removed. Run: sudo rm -rf $NEEDLE_DIR"
fi

### Step 5: Final message
print_success "🎉 Uninstallation complete!"
echo ""
echo "📋 What was removed:"
echo "  - Needle installation at ~/.needle"
echo "  - needlectl binary"
[ "$REMOVE_DOCKER_VOLUMES" = true ] && echo "  - Docker volumes (indexed data)"
echo ""
echo "📋 What was kept:"
echo "  - Docker images (can be removed with 'docker system prune -a')"
[ "$REMOVE_DOCKER_VOLUMES" != true ] && echo "  - Docker volumes (indexed data)"
echo ""
echo "To reinstall Needle, run:"
echo "  curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/install-oneliner.sh | bash"
