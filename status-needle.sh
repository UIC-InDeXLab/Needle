#!/bin/bash

# Check Needle Services Status (Unified)
echo "📊 Needle Services Status"
echo "========================"

# Embedded paths from installation
NEEDLE_DIR="/home/mahdi/Projects/Needle"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Change to Needle directory
cd "${NEEDLE_DIR}"

# Check if we're in the right directory
if [ ! -f "scripts/install.sh" ]; then
    echo "Needle installation not found at ${NEEDLE_DIR}"
    exit 1
fi

# Check backend
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        print_success "Backend: Running (PID: $BACKEND_PID)"
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Backend API: Responding"
        else
            print_warning "Backend API: Not responding (may still be starting)"
        fi
    else
        print_error "Backend: Not running (stale PID file)"
    fi
else
    print_error "Backend: Not running"
fi

# Check image-generator-hub
if [ -f "logs/image-generator-hub.pid" ]; then
    IMG_GEN_PID=$(cat logs/image-generator-hub.pid)
    if kill -0 $IMG_GEN_PID 2>/dev/null; then
        print_success "Image-generator-hub: Running (PID: $IMG_GEN_PID)"
        if curl -s http://localhost:8010/health > /dev/null 2>&1; then
            print_success "Image-generator-hub API: Responding"
        else
            print_warning "Image-generator-hub API: Not responding (may still be starting)"
        fi
    else
        print_error "Image-generator-hub: Not running (stale PID file)"
    fi
else
    print_warning "Image-generator-hub: Not running"
fi

# Check infrastructure services
print_status "Infrastructure Services (Docker):"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(postgres|milvus|etcd|minio)" || print_warning "No infrastructure services running"
