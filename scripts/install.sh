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
    OS="macos"
    print_status "Detected macOS"
else
    SHELL_RC_FILE="${HOME}/.bashrc"
    OS="linux"
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

# Change to NEEDLE_DIR to ensure all paths are correct
cd "$NEEDLE_DIR"

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
    print_status "Try running: git submodule update --init --recursive"
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

# First check if needlectl is already installed and working
if command -v needlectl &> /dev/null && needlectl --version > /dev/null 2>&1; then
    print_success "needlectl is already installed and working"
    NEEDLECTL_VERSION=$(needlectl --version 2>&1 | head -1)
    print_status "Current version: $NEEDLECTL_VERSION"
else
    print_status "Installing needlectl binary..."
    
    NEEDLECTL_INSTALLED=false
    
    # Download the latest needlectl binary
    print_status "Downloading latest needlectl binary for $OS..."
    RELEASE_URL="https://github.com/UIC-InDeXLab/Needle/releases/latest/download/needlectl-$OS"
    
    # Try to download the binary
    if curl -L -f -o /tmp/needlectl "$RELEASE_URL" 2>/dev/null; then
        # Check if the downloaded file is valid (executable binary)
        if [ -s /tmp/needlectl ] && file /tmp/needlectl | grep -qE "(executable|ELF|Mach-O)"; then
            chmod +x /tmp/needlectl
            
            # Try to install - first try without sudo, then with sudo
            if [ -w /usr/local/bin ]; then
                mv /tmp/needlectl /usr/local/bin/needlectl
                print_success "needlectl binary installed to /usr/local/bin/needlectl"
                NEEDLECTL_INSTALLED=true
            elif sudo -n true 2>/dev/null; then
                # sudo without password works
                sudo mv /tmp/needlectl /usr/local/bin/needlectl
                print_success "needlectl binary installed to /usr/local/bin/needlectl"
                NEEDLECTL_INSTALLED=true
            else
                print_warning "Cannot write to /usr/local/bin without sudo password"
                print_status "Installing needlectl to local bin directory instead..."
                mkdir -p "$HOME/.local/bin"
                mv /tmp/needlectl "$HOME/.local/bin/needlectl"
                print_success "needlectl binary installed to $HOME/.local/bin/needlectl"
                print_warning "Make sure $HOME/.local/bin is in your PATH"
                NEEDLECTL_INSTALLED=true
            fi
        else
            print_warning "Downloaded file appears to be invalid"
            rm -f /tmp/needlectl
        fi
    else
        print_warning "Failed to download needlectl from GitHub releases"
    fi
    
    # Fallback to building from source if download failed
    if [ "$NEEDLECTL_INSTALLED" = false ]; then
        print_status "Building needlectl from source..."
        
        if [ -f "needlectl/needlectl.py" ]; then
            cd needlectl
            
            # Deactivate any active virtual environment before building
            deactivate 2>/dev/null || true
            
            # Build needlectl binary using PyInstaller (build.sh creates its own venv)
            print_status "Building needlectl binary with PyInstaller..."
            chmod +x build.sh
            if ./build.sh 2>&1; then
                if [ -f "dist/needlectl" ]; then
                    # Try to install to system location or local bin
                    if [ -w /usr/local/bin ]; then
                        cp dist/needlectl /usr/local/bin/needlectl
                        chmod +x /usr/local/bin/needlectl
                        print_success "needlectl binary installed to /usr/local/bin/needlectl"
                    elif sudo -n true 2>/dev/null; then
                        sudo cp dist/needlectl /usr/local/bin/needlectl
                        sudo chmod +x /usr/local/bin/needlectl
                        print_success "needlectl binary installed to /usr/local/bin/needlectl"
                    else
                        mkdir -p "$HOME/.local/bin"
                        cp dist/needlectl "$HOME/.local/bin/needlectl"
                        chmod +x "$HOME/.local/bin/needlectl"
                        print_success "needlectl binary installed to $HOME/.local/bin/needlectl"
                        print_warning "Make sure $HOME/.local/bin is in your PATH"
                    fi
                else
                    print_warning "Failed to build needlectl binary - needlectl will not be available"
                fi
            else
                print_warning "Failed to build needlectl binary - needlectl will not be available"
            fi
            
            cd ..
        else
            print_warning "needlectl source not found - needlectl will not be available"
        fi
    fi
    
    # Verify installation
    if command -v needlectl &> /dev/null; then
        print_success "needlectl installation verified"
    else
        print_warning "needlectl not available in PATH. You can still use ./start-needle.sh to manage services."
    fi
fi

### Step 8: Create Service Management Scripts
print_status "Creating service management scripts..."

# Create start script with embedded paths
cat > start-needle.sh << EOF
#!/bin/bash

# Start Needle Services (Unified)
set -e

echo "🚀 Starting Needle Services"
echo "=========================="

# Embedded paths from installation
NEEDLE_DIR="${NEEDLE_DIR}"
IMAGE_GEN_HUB_DIR="${IMAGE_GEN_HUB_DIR}"
HAS_GPU="${HAS_GPU}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "\${BLUE}[INFO]\${NC} \$1"
}

print_success() {
    echo -e "\${GREEN}[SUCCESS]\${NC} \$1"
}

print_error() {
    echo -e "\${RED}[ERROR]\${NC} \$1"
}

print_warning() {
    echo -e "\${YELLOW}[WARNING]\${NC} \$1"
}

# Change to Needle directory
cd "\${NEEDLE_DIR}"

# Check if we're in the right directory
if [ ! -f "scripts/install.sh" ]; then
    print_error "Needle installation not found at \${NEEDLE_DIR}"
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
export SERVICE__USE_CUDA=\${HAS_GPU}
export SERVICE__CONFIG_DIR_PATH="\${NEEDLE_DIR}/configs/"
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
if [ -d "\${IMAGE_GEN_HUB_DIR}" ] && [ -d "\${IMAGE_GEN_HUB_DIR}/.venv" ]; then
    print_status "Starting image-generator-hub..."
    cd "\${IMAGE_GEN_HUB_DIR}"
    source .venv/bin/activate
    nohup uvicorn main:app --host 0.0.0.0 --port 8010 > "\${NEEDLE_DIR}/logs/image-generator-hub.log" 2>&1 &
    echo \$! > "\${NEEDLE_DIR}/logs/image-generator-hub.pid"
    deactivate
    cd "\${NEEDLE_DIR}"
    print_success "Image-generator-hub started on port 8010"
else
    print_warning "ImageGeneratorsHub not found or not set up. Skipping image generator."
fi

# Start backend
print_status "Starting Needle backend..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > "\${NEEDLE_DIR}/logs/backend.log" 2>&1 &
echo \$! > "\${NEEDLE_DIR}/logs/backend.pid"
deactivate
cd "\${NEEDLE_DIR}"

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

# Create stop script with embedded paths
cat > stop-needle.sh << EOF
#!/bin/bash

# Stop Needle Services (Unified)
set -e

echo "🛑 Stopping Needle Services"
echo "=========================="

# Embedded paths from installation
NEEDLE_DIR="${NEEDLE_DIR}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "\${BLUE}[INFO]\${NC} \$1"
}

print_success() {
    echo -e "\${GREEN}[SUCCESS]\${NC} \$1"
}

# Change to Needle directory
cd "\${NEEDLE_DIR}"

# Check if we're in the right directory
if [ ! -f "scripts/install.sh" ]; then
    echo "Needle installation not found at \${NEEDLE_DIR}"
    exit 1
fi

# Stop backend
if [ -f "logs/backend.pid" ]; then
    print_status "Stopping backend..."
    BACKEND_PID=\$(cat logs/backend.pid)
    if kill -0 \$BACKEND_PID 2>/dev/null; then
        kill \$BACKEND_PID
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
    IMG_GEN_PID=\$(cat logs/image-generator-hub.pid)
    if kill -0 \$IMG_GEN_PID 2>/dev/null; then
        kill \$IMG_GEN_PID
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

# Create status script with embedded paths
cat > status-needle.sh << EOF
#!/bin/bash

# Check Needle Services Status (Unified)
echo "📊 Needle Services Status"
echo "========================"

# Embedded paths from installation
NEEDLE_DIR="${NEEDLE_DIR}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "\${BLUE}[INFO]\${NC} \$1"
}

print_success() {
    echo -e "\${GREEN}[SUCCESS]\${NC} \$1"
}

print_error() {
    echo -e "\${RED}[ERROR]\${NC} \$1"
}

print_warning() {
    echo -e "\${YELLOW}[WARNING]\${NC} \$1"
}

# Change to Needle directory
cd "\${NEEDLE_DIR}"

# Check if we're in the right directory
if [ ! -f "scripts/install.sh" ]; then
    echo "Needle installation not found at \${NEEDLE_DIR}"
    exit 1
fi

# Check backend
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=\$(cat logs/backend.pid)
    if kill -0 \$BACKEND_PID 2>/dev/null; then
        print_success "Backend: Running (PID: \$BACKEND_PID)"
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
    IMG_GEN_PID=\$(cat logs/image-generator-hub.pid)
    if kill -0 \$IMG_GEN_PID 2>/dev/null; then
        print_success "Image-generator-hub: Running (PID: \$IMG_GEN_PID)"
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
EOF

# Make scripts executable
chmod +x start-needle.sh stop-needle.sh status-needle.sh

print_success "Service management scripts created"

### Step 9: Download and Install UI Artifacts (Optional)
print_status "Attempting to download pre-built UI artifacts from GitHub releases..."

# Ensure UI directory exists
mkdir -p ui

# Download the latest UI build artifacts
print_status "Downloading latest UI build for $OS..."
UI_RELEASE_URL="https://github.com/UIC-InDeXLab/Needle/releases/latest/download/ui-build-$OS.tar.gz"

UI_INSTALLED=false

# Try to download the UI artifacts with better error handling
if curl -L -f -o /tmp/ui-build.tar.gz "$UI_RELEASE_URL" 2>/dev/null; then
    # Check if the downloaded file is valid (not a 404 page)
    if [ -s /tmp/ui-build.tar.gz ] && file /tmp/ui-build.tar.gz | grep -q "gzip"; then
        # Extract UI build artifacts
        print_status "Extracting UI build artifacts..."
        if tar -xzf /tmp/ui-build.tar.gz -C ui 2>/dev/null; then
            rm -f /tmp/ui-build.tar.gz
            print_success "UI build artifacts installed successfully"
            UI_INSTALLED=true
        else
            print_warning "Failed to extract UI build artifacts - UI will need to be built manually"
            rm -f /tmp/ui-build.tar.gz
        fi
    else
        print_warning "Downloaded UI file appears to be invalid - UI will need to be built manually"
        rm -f /tmp/ui-build.tar.gz
    fi
else
    print_warning "UI artifacts not available from GitHub releases - UI will need to be built manually"
    print_status "You can build the UI manually later with: cd ui && npm install && npm run build"
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
