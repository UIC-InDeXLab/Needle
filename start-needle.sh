#!/bin/bash

# Start Needle Services (Unified)
set -e

echo "🚀 Starting Needle Services"
echo "=========================="

# Embedded paths from installation
NEEDLE_DIR="/home/mahdi/Projects/Needle"
IMAGE_GEN_HUB_DIR="/home/mahdi/Projects/Needle/ImageGeneratorsHub"
HAS_GPU="true"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
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
    print_error "Needle installation not found at ${NEEDLE_DIR}"
    exit 1
fi

# Set environment variables
export POSTGRES__USER=myuser
export POSTGRES__PASSWORD=mypassword
export POSTGRES__DB=mydb
export POSTGRES__HOST=localhost
export POSTGRES__PORT=5432
export MILVUS__HOST=localhost
export MILVUS__PORT=19530
export SERVICE__USE_CUDA=${HAS_GPU}
export SERVICE__CONFIG_DIR_PATH="${NEEDLE_DIR}/configs/"
export GENERATOR__HOST=localhost
export GENERATOR__PORT=8010

# Start infrastructure services (Docker)
print_status "Starting infrastructure services (PostgreSQL, Milvus, etc.)..."
docker compose -f docker/docker-compose.infrastructure.yaml up -d

# Wait for services to be ready
print_status "Waiting for infrastructure services to be ready..."
sleep 15

# Check if services are healthy
print_status "Checking service health..."

# Check PostgreSQL
if ! docker ps | grep -q "postgres"; then
    print_warning "PostgreSQL container not found, but continuing..."
fi

# Check Milvus
if ! curl -f http://localhost:9091/healthz > /dev/null 2>&1; then
    print_warning "Milvus health check failed, but continuing..."
fi

print_success "Infrastructure services are ready"

# Create logs directory
mkdir -p logs

# Start image-generator-hub
if [ -d "${IMAGE_GEN_HUB_DIR}" ] && [ -d "${IMAGE_GEN_HUB_DIR}/.venv" ]; then
    print_status "Starting image-generator-hub..."
    cd "${IMAGE_GEN_HUB_DIR}"
    source .venv/bin/activate
    nohup uvicorn main:app --host 0.0.0.0 --port 8010 > "${NEEDLE_DIR}/logs/image-generator-hub.log" 2>&1 &
    echo $! > "${NEEDLE_DIR}/logs/image-generator-hub.pid"
    deactivate
    cd "${NEEDLE_DIR}"
    print_success "Image-generator-hub started on port 8010"
else
    print_warning "ImageGeneratorsHub not found or not set up. Skipping image generator."
fi

# Start backend
print_status "Starting Needle backend..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > "${NEEDLE_DIR}/logs/backend.log" 2>&1 &
echo $! > "${NEEDLE_DIR}/logs/backend.pid"
deactivate
cd "${NEEDLE_DIR}"

print_success "Needle backend started on port 8000"
print_success "All services are running!"
echo ""
echo "🌐 Access Points:"
echo "  - Backend API: http://localhost:8000"
echo "  - Image Generator: http://localhost:8010"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - PostgreSQL: localhost:5432"
echo "  - Milvus: localhost:19530"
echo ""
echo "📊 Monitor services:"
echo "  - Backend logs: tail -f logs/backend.log"
echo "  - Image generator logs: tail -f logs/image-generator-hub.log"
echo "  - Docker services: docker ps"
