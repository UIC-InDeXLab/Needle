#!/bin/bash

# Stop Needle Services (Unified)
set -e

echo "🛑 Stopping Needle Services"
echo "=========================="

# Embedded paths from installation
NEEDLE_DIR="/home/mahdi/Projects/Needle"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Change to Needle directory
cd "${NEEDLE_DIR}"

# Check if we're in the right directory
if [ ! -f "scripts/install.sh" ]; then
    echo "Needle installation not found at ${NEEDLE_DIR}"
    exit 1
fi

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
docker compose -f docker/docker-compose.infrastructure.yaml down

print_success "All services stopped"
