#!/bin/bash

# Needle Unified Uninstallation Script
# Removes virtual environments, stops services, and cleans up

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

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEEDLE_DIR="$SCRIPT_DIR"
IMAGE_GEN_HUB_DIR="$SCRIPT_DIR/../ImageGeneratorsHub"

print_status "Needle directory: $NEEDLE_DIR"
print_status "ImageGeneratorsHub directory: $IMAGE_GEN_HUB_DIR"

# Confirm uninstallation
read -p "Are you sure you want to uninstall Needle? This will stop all services and remove virtual environments. (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Uninstallation cancelled."
    exit 0
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
if [ -f ".env" ]; then
    rm -f .env
    print_success "Environment configuration removed"
fi

if [ -f ".env.venv" ]; then
    rm -f .env.venv
    print_success "Old environment configuration removed"
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

### Step 6: Ask about removing ImageGeneratorsHub directory
echo ""
print_warning "ImageGeneratorsHub directory found at: ${IMAGE_GEN_HUB_DIR}"
read -p "Do you want to remove the entire ImageGeneratorsHub directory? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "${IMAGE_GEN_HUB_DIR}" ]; then
        print_status "Removing ImageGeneratorsHub directory..."
        rm -rf "${IMAGE_GEN_HUB_DIR}"
        print_success "ImageGeneratorsHub directory removed"
    fi
else
    print_status "ImageGeneratorsHub directory kept (only virtual environment removed)"
fi

### Step 7: Ask about removing Docker volumes
echo ""
print_warning "Docker volumes may contain indexed data and images"
read -p "Do you want to remove Docker volumes? This will delete all indexed data. (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Removing Docker volumes..."
    if [ -d "volumes" ]; then
        rm -rf volumes
        print_success "Docker volumes removed"
    fi
    
    # Also remove any orphaned volumes
    print_status "Cleaning up orphaned Docker volumes..."
    docker volume prune -f
    print_success "Orphaned volumes cleaned up"
else
    print_status "Docker volumes kept (indexed data preserved)"
fi

### Step 8: Final cleanup
print_status "Performing final cleanup..."

# Remove any remaining PID files
find . -name "*.pid" -type f -delete 2>/dev/null || true

# Remove any remaining log files
find . -name "*.log" -type f -delete 2>/dev/null || true

print_success "Final cleanup completed"

### Step 9: Final message
print_success "🎉 Uninstallation complete!"
echo ""
echo "📋 What was removed:"
echo "  - Backend virtual environment"
echo "  - ImageGeneratorsHub virtual environment"
echo "  - Service management scripts"
echo "  - Configuration files"
echo "  - Log files and PID files"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  - Docker volumes (indexed data)"
fi
echo ""
echo "📋 What was kept:"
echo "  - Source code (backend/, docker/, etc.)"
echo "  - Docker images (can be removed with 'docker system prune')"
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "  - Docker volumes (indexed data)"
fi
echo ""
print_warning "To completely remove Docker images, run: docker system prune -a"
print_warning "To reinstall, run: ./scripts/install.sh"
