#!/bin/bash

# Needle Unified Uninstallation Script
# Removes virtual environments, stops services, and cleans up
# Can be run from within Needle directory or via one-liner:
#   curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/uninstall.sh | bash

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
echo "This will stop all services and remove virtual environments"
echo ""

# Detect Needle installation directory
# Priority: 1) Current directory if it's a Needle installation
#           2) ~/.needle (one-liner installation)
#           3) Script directory's parent (manual installation)

detect_needle_dir() {
    # Check if current directory is a Needle installation
    if [ -f "scripts/install.sh" ] && [ -d "backend" ]; then
        echo "$(pwd)"
        return 0
    fi
    
    # Check default one-liner installation path
    if [ -d "$HOME/.needle" ] && [ -f "$HOME/.needle/scripts/install.sh" ]; then
        echo "$HOME/.needle"
        return 0
    fi
    
    # Check script directory's parent (for manual installations)
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "/dev/stdin" ]; then
        local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
        local parent_dir="$(dirname "$script_dir")"
        if [ -f "$parent_dir/scripts/install.sh" ] && [ -d "$parent_dir/backend" ]; then
            echo "$parent_dir"
            return 0
        fi
    fi
    
    return 1
}

NEEDLE_DIR=""
if NEEDLE_DIR=$(detect_needle_dir); then
    print_status "Found Needle installation at: $NEEDLE_DIR"
else
    print_error "Could not find Needle installation."
    print_status "Checked locations:"
    print_status "  - Current directory: $(pwd)"
    print_status "  - Default location: $HOME/.needle"
    print_status ""
    print_status "Please either:"
    print_status "  1. Run this script from within the Needle directory"
    print_status "  2. Or ensure Needle is installed at ~/.needle"
    exit 1
fi

IMAGE_GEN_HUB_DIR="$NEEDLE_DIR/ImageGeneratorsHub"

print_status "Needle directory: $NEEDLE_DIR"

# Change to Needle directory
cd "$NEEDLE_DIR"

# Confirm uninstallation - handle both interactive and non-interactive modes
if [ -t 0 ]; then
    # Interactive mode
    read -p "Are you sure you want to uninstall Needle? This will stop all services and remove virtual environments. (y/N): " -n 1 -r
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

### Step 1: Stop all services
print_status "Stopping all services..."

# Stop backend
if [ -f "logs/backend.pid" ]; then
    print_status "Stopping backend..."
    BACKEND_PID=$(cat logs/backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        print_success "Backend stopped"
    else
        print_status "Backend was not running"
    fi
    rm -f logs/backend.pid
else
    print_status "No backend PID file found"
fi

# Stop image-generator-hub
if [ -f "logs/image-generator-hub.pid" ]; then
    print_status "Stopping image-generator-hub..."
    IMG_GEN_PID=$(cat logs/image-generator-hub.pid)
    if kill -0 $IMG_GEN_PID 2>/dev/null; then
        kill $IMG_GEN_PID
        print_success "Image-generator-hub stopped"
    else
        print_status "Image-generator-hub was not running"
    fi
    rm -f logs/image-generator-hub.pid
else
    print_status "No image-generator-hub PID file found"
fi

# Stop infrastructure services
print_status "Stopping infrastructure services..."
if [ -f "docker/docker-compose.infrastructure.yaml" ]; then
    docker compose -f docker/docker-compose.infrastructure.yaml down
    print_success "Infrastructure services stopped"
else
    print_warning "Infrastructure docker-compose file not found"
fi

### Step 2: Remove virtual environments
print_status "Removing virtual environments..."

# Remove backend virtual environment
if [ -d "backend/venv" ]; then
    print_status "Removing backend virtual environment..."
    rm -rf backend/venv
    print_success "Backend virtual environment removed"
else
    print_status "Backend virtual environment not found"
fi

# Remove ImageGeneratorsHub virtual environment
if [ -d "${IMAGE_GEN_HUB_DIR}/.venv" ]; then
    print_status "Removing ImageGeneratorsHub virtual environment..."
    rm -rf "${IMAGE_GEN_HUB_DIR}/.venv"
    print_success "ImageGeneratorsHub virtual environment removed"
else
    print_status "ImageGeneratorsHub virtual environment not found"
fi

### Step 3: Remove logs and PID files
print_status "Cleaning up logs and PID files..."
if [ -d "logs" ]; then
    rm -rf logs
    print_success "Logs directory removed"
fi

### Step 4: Remove configuration files
print_status "Removing configuration files..."
# Note: No .env file to remove - configuration is now handled via configs/ directory

# Legacy cleanup - remove old .env.venv if it exists
if [ -f ".env.venv" ]; then
    rm -f .env.venv
    print_success "Legacy .env.venv removed"
fi

### Step 5: Remove service management scripts
print_status "Removing service management scripts..."
if [ -f "start-needle.sh" ]; then
    rm -f start-needle.sh
    print_success "Start script removed"
fi

if [ -f "stop-needle.sh" ]; then
    rm -f stop-needle.sh
    print_success "Stop script removed"
fi

if [ -f "status-needle.sh" ]; then
    rm -f status-needle.sh
    print_success "Status script removed"
fi

# Remove old venv scripts
for script in start-needle-venv.sh stop-needle-venv.sh status-needle-venv.sh; do
    if [ -f "$script" ]; then
        rm -f "$script"
        print_success "Old $script removed"
    fi
done

### Step 6: Remove needlectl binary
if [ -f "/usr/local/bin/needlectl" ]; then
    print_status "Removing needlectl binary..."
    sudo rm -f /usr/local/bin/needlectl 2>/dev/null || rm -f /usr/local/bin/needlectl 2>/dev/null || print_warning "Could not remove /usr/local/bin/needlectl (may need sudo)"
    if [ ! -f "/usr/local/bin/needlectl" ]; then
        print_success "needlectl binary removed"
    fi
fi

### Step 7: Handle optional removals based on interactive/non-interactive mode
REMOVE_IMAGE_GEN_HUB=false
REMOVE_DOCKER_VOLUMES=false
REMOVE_NEEDLE_DIR=false

if [ -t 0 ]; then
    # Interactive mode - ask user
    echo ""
    if [ -d "${IMAGE_GEN_HUB_DIR}" ]; then
        print_warning "ImageGeneratorsHub directory found at: ${IMAGE_GEN_HUB_DIR}"
        read -p "Do you want to remove the entire ImageGeneratorsHub directory? (y/N): " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] && REMOVE_IMAGE_GEN_HUB=true
    fi
    
    echo ""
    print_warning "Docker volumes may contain indexed data and images"
    read -p "Do you want to remove Docker volumes? This will delete all indexed data. (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && REMOVE_DOCKER_VOLUMES=true
    
    # Ask about removing entire Needle directory (especially for one-liner installs)
    if [ "$NEEDLE_DIR" = "$HOME/.needle" ]; then
        echo ""
        print_warning "This appears to be a one-liner installation at $NEEDLE_DIR"
        read -p "Do you want to remove the entire Needle directory? (y/N): " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] && REMOVE_NEEDLE_DIR=true
    fi
else
    # Non-interactive mode - keep data by default
    print_status "Non-interactive mode: Keeping ImageGeneratorsHub directory and Docker volumes"
    print_status "To remove these, run the uninstall script interactively"
fi

# Execute removals based on user choices
if [ "$REMOVE_IMAGE_GEN_HUB" = true ] && [ -d "${IMAGE_GEN_HUB_DIR}" ]; then
    print_status "Removing ImageGeneratorsHub directory..."
    rm -rf "${IMAGE_GEN_HUB_DIR}"
    print_success "ImageGeneratorsHub directory removed"
fi

if [ "$REMOVE_DOCKER_VOLUMES" = true ]; then
    print_status "Removing Docker volumes..."
    if [ -d "volumes" ]; then
        rm -rf volumes
        print_success "Docker volumes removed"
    fi
    
    # Also remove any orphaned volumes
    print_status "Cleaning up orphaned Docker volumes..."
    docker volume prune -f 2>/dev/null || true
    print_success "Orphaned volumes cleaned up"
fi

### Step 8: Final cleanup
print_status "Performing final cleanup..."

# Remove any remaining PID files
find . -name "*.pid" -type f -delete 2>/dev/null || true

# Remove any remaining log files in the logs directory
find . -path "./logs/*.log" -type f -delete 2>/dev/null || true

print_success "Final cleanup completed"

# Remove entire Needle directory if requested (for one-liner installs)
if [ "$REMOVE_NEEDLE_DIR" = true ]; then
    print_status "Removing entire Needle directory at $NEEDLE_DIR..."
    cd "$HOME"
    rm -rf "$NEEDLE_DIR"
    print_success "Needle directory removed"
fi

### Step 9: Final message
print_success "🎉 Uninstallation complete!"
echo ""
echo "📋 What was removed:"
echo "  - Backend virtual environment"
echo "  - ImageGeneratorsHub virtual environment"
echo "  - Service management scripts"
echo "  - needlectl binary"
echo "  - Log files and PID files"
[ "$REMOVE_IMAGE_GEN_HUB" = true ] && echo "  - ImageGeneratorsHub directory"
[ "$REMOVE_DOCKER_VOLUMES" = true ] && echo "  - Docker volumes (indexed data)"
[ "$REMOVE_NEEDLE_DIR" = true ] && echo "  - Entire Needle directory"
echo ""
echo "📋 What was kept:"
[ "$REMOVE_NEEDLE_DIR" != true ] && echo "  - Source code (backend/, docker/, etc.)"
echo "  - Docker images (can be removed with 'docker system prune')"
[ "$REMOVE_DOCKER_VOLUMES" != true ] && echo "  - Docker volumes (indexed data)"
echo ""
print_warning "To completely remove Docker images, run: docker system prune -a"
[ "$REMOVE_NEEDLE_DIR" != true ] && print_warning "To reinstall, run: ./scripts/install.sh"
