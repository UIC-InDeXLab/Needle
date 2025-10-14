#!/bin/bash

# Needle Unified Installation Script
# Sets up two virtual environments (backend and image-generator-hub) + Docker infrastructure
# Works on both Linux and macOS with automatic GPU detection
# Usage: ./install.sh [fast|balanced|accurate]

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

echo -e "${GREEN}🪡 Needle Unified Installation${NC}"
echo "================================="
echo "Setting up virtual environments + Docker infrastructure"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEEDLE_DIR="$SCRIPT_DIR"
IMAGE_GEN_HUB_DIR="$SCRIPT_DIR/../ImageGeneratorsHub"

print_status "Needle directory: $NEEDLE_DIR"
print_status "ImageGeneratorsHub directory: $IMAGE_GEN_HUB_DIR"

# Configuration selection
CONFIG_MODE="${1:-}"
if [ -z "$CONFIG_MODE" ]; then
    echo ""
    print_status "Choose your performance configuration:"
    echo "1) Fast (Default) - Single CLIP model, fastest indexing and retrieval"
    echo "2) Balanced - 4 models with balanced performance and accuracy"
    echo "3) Accurate - 6 models with highest accuracy but slower performance"
    echo ""
    
    while true; do
        read -p "Enter your choice (1-3) [default: 1]: " config_choice
        case $config_choice in
            1|"")
                CONFIG_MODE="fast"
                break
                ;;
            2)
                CONFIG_MODE="balanced"
                break
                ;;
            3)
                CONFIG_MODE="accurate"
                break
                ;;
            *)
                print_error "Invalid choice. Please enter 1, 2, or 3."
                ;;
        esac
    done
else
    # Validate provided configuration
    case $CONFIG_MODE in
        fast|balanced|accurate)
            print_status "Using provided configuration: $CONFIG_MODE"
            ;;
        *)
            print_error "Invalid configuration: $CONFIG_MODE. Must be one of: fast, balanced, accurate"
            exit 1
            ;;
    esac
fi

print_success "Selected ${CONFIG_MODE} configuration"

# Detect OS
OS_TYPE="${OSTYPE}"
if [[ "$OS_TYPE" == "darwin"* ]]; then
    SHELL_RC_FILE="${HOME}/.zshrc"
    print_status "Detected macOS"
else
    SHELL_RC_FILE="${HOME}/.bashrc"
    print_status "Detected Linux"
fi

### Step 1: Check Dependencies
print_status "Checking system dependencies..."

# Check Python 3.12+
if ! command -v python3.12 &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.12+ and try again."
        exit 1
    else
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if command -v bc &> /dev/null && [ "$(echo "$PYTHON_VERSION < 3.12" | bc -l)" -eq 1 ]; then
            print_warning "Python version $PYTHON_VERSION detected. Python 3.12+ is recommended."
        fi
        PYTHON_CMD="python3"
    fi
else
    PYTHON_CMD="python3.12"
fi

print_success "Using Python: $PYTHON_CMD"

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker not installed. Please install Docker and re-run."
    exit 1
fi

# Check docker compose plugin
if ! docker compose version &> /dev/null; then
    print_error "docker compose plugin not installed. Please install and re-run."
    exit 1
fi

print_success "Docker and docker compose found."

# Check Git
if ! command -v git &> /dev/null; then
    print_error "Git not installed. Please install Git and re-run."
    exit 1
fi

print_success "Git found."

### Step 2: Check for GPU availability
HAS_GPU=false
if [[ "$OS_TYPE" == "darwin"* ]]; then
    # Check for Metal Performance Shaders (MPS) support
    if python3 -c "import torch; print(torch.backends.mps.is_available())" 2>/dev/null | grep -q "True"; then
        print_success "Metal Performance Shaders (MPS) detected on macOS."
        HAS_GPU=true
    else
        print_warning "No MPS support detected on macOS. Using CPU mode."
    fi
else
    if command -v nvidia-smi &> /dev/null; then
        print_status "nvidia-smi found, checking GPU availability..."
        if nvidia-smi &> /dev/null; then
            print_success "NVIDIA GPU detected and accessible."
            HAS_GPU=true
        else
            print_warning "GPU detected but not accessible. Using CPU mode."
        fi
    else
        print_warning "No GPU detected, using CPU mode."
    fi
fi

### Step 3: Initialize and update submodules
print_status "Setting up ImageGeneratorsHub submodule..."

# Initialize and update submodules
print_status "Initializing git submodules..."
git submodule init
git submodule update --recursive

# Check if ImageGeneratorsHub submodule is properly initialized
if [ -d "ImageGeneratorsHub" ] && [ -f "ImageGeneratorsHub/.git" ]; then
    print_success "ImageGeneratorsHub submodule initialized"
    IMAGE_GEN_HUB_DIR="${NEEDLE_DIR}/ImageGeneratorsHub"
    print_status "ImageGeneratorsHub directory: $IMAGE_GEN_HUB_DIR"
else
    print_error "Failed to initialize ImageGeneratorsHub submodule"
    exit 1
fi

### Step 4: Setup Backend Virtual Environment
print_status "Setting up backend virtual environment..."

if [ ! -d "backend/venv" ]; then
    print_status "Creating backend virtual environment..."
    cd backend
    $PYTHON_CMD -m venv venv
    cd ..
    print_success "Backend virtual environment created"
else
    print_status "Backend virtual environment already exists"
fi

# Install backend dependencies
print_status "Installing backend dependencies..."
cd backend
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..
print_success "Backend dependencies installed"

### Step 5: Setup ImageGeneratorsHub Virtual Environment
print_status "Setting up ImageGeneratorsHub virtual environment..."

cd "${IMAGE_GEN_HUB_DIR}"

if [ ! -d ".venv" ]; then
    print_status "Creating ImageGeneratorsHub virtual environment..."
    $PYTHON_CMD -m venv .venv
    print_success "ImageGeneratorsHub virtual environment created"
else
    print_status "ImageGeneratorsHub virtual environment already exists"
fi

source .venv/bin/activate

if [ -f "requirements.txt" ]; then
    print_status "Installing ImageGeneratorsHub dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "ImageGeneratorsHub dependencies installed"
else
    print_warning "No requirements.txt found for ImageGeneratorsHub"
fi

cd "${NEEDLE_DIR}"

### Step 6: Create Configuration Files
print_status "Creating configuration files for ${CONFIG_MODE} mode..."

# Create .env file for the unified setup
cat > .env << EOF
# Needle Unified Configuration - ${CONFIG_MODE} mode
# Backend Configuration
POSTGRES__USER=myuser
POSTGRES__PASSWORD=mypassword
POSTGRES__DB=mydb
POSTGRES__HOST=localhost
POSTGRES__PORT=5432

MILVUS__HOST=localhost
MILVUS__PORT=19530

SERVICE__USE_CUDA=${HAS_GPU}
SERVICE__CONFIG_DIR_PATH=${NEEDLE_DIR}/configs/${CONFIG_MODE}/

GENERATOR__HOST=localhost
GENERATOR__PORT=8010

# Directory Configuration
DIRECTORY__NUM_WATCHER_WORKERS=4
DIRECTORY__BATCH_SIZE=50
DIRECTORY__RECURSIVE_INDEXING=true
DIRECTORY__CONSISTENCY_CHECK_INTERVAL=1800

# Query Configuration
QUERY__NUM_IMAGES_TO_RETRIEVE=10
QUERY__NUM_IMAGES_TO_GENERATE=1
QUERY__GENERATED_IMAGE_SIZE=SMALL
QUERY__NUM_ENGINES_TO_USE=1
QUERY__USE_FALLBACK=true
QUERY__INCLUDE_BASE_IMAGES_IN_PREVIEW=false
EOF

# Copy configuration files from the selected mode
print_status "Copying ${CONFIG_MODE} configuration files..."
if [ -d "configs/${CONFIG_MODE}" ]; then
    cp -r "configs/${CONFIG_MODE}"/* "configs/"
    print_success "Configuration files copied from configs/${CONFIG_MODE}/"
else
    print_warning "Configuration directory configs/${CONFIG_MODE} not found, using default configs"
fi

print_success "Environment configuration created for ${CONFIG_MODE} mode"

### Step 7: Install needlectl
print_status "Installing needlectl..."

# Install needlectl to /usr/local/bin
if [ -f "needlectl/needlectl.py" ]; then
    # Install Python dependencies for needlectl
    cd needlectl
    pip install -r requirements.txt
    cd ..
    
    # Create needlectl binary
    cat > /tmp/needlectl << 'EOF'
#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add the needlectl directory to Python path
needlectl_dir = Path("/usr/local/lib/needlectl")
sys.path.insert(0, str(needlectl_dir))

from cli.main import app

if __name__ == "__main__":
    app()
EOF

    # Copy needlectl to system location
    sudo cp /tmp/needlectl /usr/local/bin/needlectl
    sudo chmod +x /usr/local/bin/needlectl
    rm /tmp/needlectl
    
    # Copy needlectl directory to system location
    sudo cp -r needlectl /usr/local/lib/needlectl
    
    print_success "needlectl installed to /usr/local/bin/needlectl"
else
    print_warning "needlectl directory not found, skipping needlectl installation"
fi

### Step 8: Create Service Management Scripts
print_status "Creating service management scripts..."

# Create start script
cat > start-needle.sh << 'EOF'
#!/bin/bash

# Start Needle Services (Unified)
set -e

echo "🚀 Starting Needle Services"
echo "=========================="

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

# Check if we're in the right directory
if [ ! -f "install.sh" ]; then
    print_error "Please run this script from the Needle project root directory"
    exit 1
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Start infrastructure services (Docker)
print_status "Starting infrastructure services (PostgreSQL, Milvus, etc.)..."
docker compose -f docker/docker-compose.infrastructure.yaml up -d

# Wait for services to be ready
print_status "Waiting for infrastructure services to be ready..."
sleep 15

# Check if services are healthy
print_status "Checking service health..."

# Check PostgreSQL
if ! docker ps | grep -q "postgres.*healthy"; then
    print_warning "PostgreSQL health check failed, but continuing..."
fi

# Check Milvus
if ! curl -f http://localhost:9091/healthz > /dev/null 2>&1; then
    print_warning "Milvus health check failed, but continuing..."
fi

print_success "Infrastructure services are ready"

# Create logs directory
mkdir -p logs

# Start image-generator-hub
print_status "Starting image-generator-hub..."
cd ../ImageGeneratorsHub
source .venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8010 > ../Needle/logs/image-generator-hub.log 2>&1 &
echo $! > ../Needle/logs/image-generator-hub.pid
cd ../Needle
print_success "Image-generator-hub started on port 8010"

# Start backend
print_status "Starting Needle backend..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
echo $! > ../logs/backend.pid
cd ..

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
EOF

# Create stop script
cat > stop-needle.sh << 'EOF'
#!/bin/bash

# Stop Needle Services (Unified)
set -e

echo "🛑 Stopping Needle Services"
echo "=========================="

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

# Check if we're in the right directory
if [ ! -f "install.sh" ]; then
    echo "Please run this script from the Needle project root directory"
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
EOF

# Create status script
cat > status-needle.sh << 'EOF'
#!/bin/bash

# Check Needle Services Status (Unified)
echo "📊 Needle Services Status"
echo "========================"

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

# Check if we're in the right directory
if [ ! -f "install.sh" ]; then
    echo "Please run this script from the Needle project root directory"
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
            print_warning "Backend API: Not responding"
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
            print_warning "Image-generator-hub API: Not responding"
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
EOF

# Make scripts executable
chmod +x start-needle.sh stop-needle.sh status-needle.sh

print_success "Service management scripts created"

### Step 9: Create logs directory
mkdir -p logs

### Step 10: Final message
print_success "🎉 Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start services: ./start-needle.sh"
echo "2. Check status: ./status-needle.sh"
echo "3. Stop services: ./stop-needle.sh"
echo ""
echo "🛠️  Using needlectl:"
echo "  - Start services: needlectl service start"
echo "  - Stop services: needlectl service stop"
echo "  - Check status: needlectl service status"
echo "  - View logs: needlectl service log [backend|image-generator-hub|infrastructure]"
echo ""
echo "🌐 Access Points:"
echo "  - Backend API: http://localhost:8000"
echo "  - Image Generator: http://localhost:8010"
echo "  - API Documentation: http://localhost:8000/docs"
echo ""
echo "📊 Configuration:"
echo "  - Mode: ${CONFIG_MODE}"
echo "  - GPU Support: ${HAS_GPU}"
echo "  - Backend: Virtual Environment"
echo "  - Image Generator: Virtual Environment"
echo "  - Infrastructure: Docker Containers"
echo ""
print_warning "Make sure to run './start-needle.sh' or 'needlectl service start' to start all services."
