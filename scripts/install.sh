#!/bin/bash

# Needle Unified Installation Script
# Sets up two virtual environments (backend and image-generator-hub) + Docker infrastructure
# Works on both Linux and macOS with automatic GPU detection
# Usage: ./scripts/install.sh [fast|balanced|accurate]

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
NEEDLE_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_GEN_HUB_DIR="$NEEDLE_DIR/ImageGeneratorsHub"

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

# Copy configuration files from the selected mode
print_status "Copying ${CONFIG_MODE} configuration files..."
if [ -d "configs/${CONFIG_MODE}" ]; then
    cp -r "configs/${CONFIG_MODE}"/* "configs/"
    print_success "Configuration files copied from configs/${CONFIG_MODE}/"
else
    print_warning "Configuration directory configs/${CONFIG_MODE} not found, using default configs"
fi

print_success "Environment configuration created for ${CONFIG_MODE} mode"

### Step 7: Download and Install needlectl Binary
print_status "Downloading and installing needlectl binary from GitHub releases..."

# Detect OS
if [[ "$OS_TYPE" == "darwin"* ]]; then
    OS="macos"
else
    OS="linux"
fi

# Download the latest needlectl binary
print_status "Downloading latest needlectl binary for $OS..."
RELEASE_URL="https://github.com/UIC-InDeXLab/Needle/releases/latest/download/needlectl-$OS"

# Try to download the binary
if curl -L -o /tmp/needlectl "$RELEASE_URL" 2>/dev/null; then
    # Check if the downloaded file is valid (not a 404 page)
    if [ -s /tmp/needlectl ] && ! grep -q "Not Found" /tmp/needlectl; then
        # Make it executable and install
        chmod +x /tmp/needlectl
        sudo mv /tmp/needlectl /usr/local/bin/needlectl
        
        print_success "needlectl binary installed to /usr/local/bin/needlectl"
        
        # Verify installation
        if needlectl --version > /dev/null 2>&1; then
            print_success "needlectl installation verified"
        else
            print_warning "needlectl installed but version check failed"
        fi
    else
        print_warning "Downloaded file appears to be invalid (404 or empty)"
        rm -f /tmp/needlectl
        print_warning "Falling back to building from source..."
    fi
fi

# Fallback to building from source if download failed or was invalid
if [ ! -f "/usr/local/bin/needlectl" ] || ! needlectl --version > /dev/null 2>&1; then
    print_status "Building needlectl from source..."
    
    if [ -f "needlectl/needlectl.py" ]; then
        cd needlectl
        
        # Install Python dependencies for needlectl
        print_status "Installing needlectl dependencies..."
        pip install -r requirements.txt
        
        # Build needlectl binary using PyInstaller
        print_status "Building needlectl binary with PyInstaller..."
        ./build.sh
        
        if [ -f "dist/needlectl" ]; then
            # Copy the built binary to system location
            print_status "Installing needlectl binary to /usr/local/bin/..."
            sudo cp dist/needlectl /usr/local/bin/needlectl
            sudo chmod +x /usr/local/bin/needlectl
            
            print_success "needlectl binary installed to /usr/local/bin/needlectl"
        else
            print_error "Failed to build needlectl binary from source"
            exit 1
        fi
        
        cd ..
    else
        print_error "needlectl source not found and download failed"
        exit 1
    fi
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
if [ ! -f "scripts/install.sh" ]; then
    print_error "Please run this script from the Needle project root directory"
    exit 1
fi

# Load environment variables from template
load_environment() {
    local env_template="scripts/env.template"
    local temp_env=$(mktemp)
    
    if [ -f "$env_template" ]; then
        # Replace template variables with actual values
        sed -e "s|{{HAS_GPU}}|${HAS_GPU:-false}|g" \
            -e "s|{{NEEDLE_DIR}}|${NEEDLE_DIR}|g" \
            "$env_template" > "$temp_env"
        
        # Load environment variables
        set -a  # automatically export all variables
        source "$temp_env"
        set +a  # disable automatic export
        
        rm -f "$temp_env"
        print_success "Environment variables loaded from template"
    else
        print_error "Environment template not found: $env_template"
        exit 1
    fi
}

# Load environment variables
load_environment

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
cd "${IMAGE_GEN_HUB_DIR}"
source .venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8010 > "${NEEDLE_DIR}/logs/image-generator-hub.log" 2>&1 &
echo $! > "${NEEDLE_DIR}/logs/image-generator-hub.pid"
cd "${NEEDLE_DIR}"
print_success "Image-generator-hub started on port 8010"

# Start backend
print_status "Starting Needle backend..."
cd backend
source venv/bin/activate
# Set the config directory path for the backend
export SERVICE__CONFIG_DIR_PATH="${NEEDLE_DIR}/configs/"
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "${NEEDLE_DIR}/logs/backend.log" 2>&1 &
echo $! > "${NEEDLE_DIR}/logs/backend.pid"
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
if [ ! -f "scripts/install.sh" ]; then
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
if [ ! -f "scripts/install.sh" ]; then
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

### Step 9: Download and Install UI Artifacts
print_status "Downloading pre-built UI artifacts from GitHub releases..."

# Download the latest UI build artifacts
print_status "Downloading latest UI build for $OS..."
UI_RELEASE_URL="https://github.com/UIC-InDeXLab/Needle/releases/latest/download/ui-build-$OS.tar.gz"

# Try to download the UI artifacts
if curl -L -o /tmp/ui-build.tar.gz "$UI_RELEASE_URL" 2>/dev/null; then
    # Extract UI build artifacts
    print_status "Extracting UI build artifacts..."
    cd ui
    tar -xzf /tmp/ui-build.tar.gz
    cd ..
    rm /tmp/ui-build.tar.gz
    
    print_success "UI build artifacts installed successfully"
else
    print_warning "Failed to download UI artifacts from GitHub releases"
    print_status "Falling back to building UI from source..."
    
    # Fallback to building from source
    if [ -d "ui" ]; then
        cd ui
        
        # Check if node_modules exists
        if [ ! -d "node_modules" ]; then
            print_status "Installing UI dependencies..."
            npm install
        fi
        
        # Build the UI
        print_status "Building React app..."
        npm run build
        
        if [ $? -eq 0 ]; then
            print_success "UI built successfully from source"
        else
            print_warning "UI build failed, but continuing with installation"
        fi
        
        cd ..
    else
        print_warning "UI directory not found, skipping UI build"
    fi
fi

### Step 10: Create logs directory
mkdir -p logs

### Step 11: Final message
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
echo "  - Start UI: needlectl ui start"
echo "  - Stop UI: needlectl ui stop"
echo "  - UI status: needlectl ui status"
echo ""
echo "🌐 Access Points:"
echo "  - Backend API: http://localhost:8000"
echo "  - Image Generator: http://localhost:8010"
echo "  - Web UI: http://localhost:3000 (when started with 'needlectl ui start')"
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
