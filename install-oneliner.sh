#!/bin/bash

# Needle One-Liner Installation Script
# This script can be run directly with curl without cloning the repository
# Usage: 
#   curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s fast
#   curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s balanced
#   curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s accurate

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

echo -e "${GREEN}🪡 Needle One-Liner Installation${NC}"
echo "====================================="
echo "This will download and install Needle with your chosen configuration"
echo ""

# Detect OS
OS_TYPE="${OSTYPE}"
if [[ "$OS_TYPE" == "darwin"* ]]; then
    print_status "Detected macOS"
else
    print_status "Detected Linux"
fi

# Check dependencies
print_status "Checking dependencies..."

# Check Python
if ! command -v python3.12 &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.12+ and try again."
        exit 1
    else
        PYTHON_CMD="python3"
    fi
else
    PYTHON_CMD="python3.12"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker not installed. Please install Docker and re-run."
    exit 1
fi

# Check docker compose
if ! docker compose version &> /dev/null; then
    print_error "docker compose plugin not installed. Please install and re-run."
    exit 1
fi

# Check Git
if ! command -v git &> /dev/null; then
    print_error "Git not installed. Please install Git and re-run."
    exit 1
fi

print_success "All dependencies found"

# Configuration selection
CONFIG_MODE="${1:-}"

if [ -n "$CONFIG_MODE" ]; then
    # Configuration provided as argument
    case $CONFIG_MODE in
        fast|balanced|accurate)
            print_status "Using provided configuration: $CONFIG_MODE"
            ;;
        *)
            print_error "Invalid configuration: $CONFIG_MODE. Must be one of: fast, balanced, accurate"
            print_status "Available options:"
            print_status "  curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s fast"
            print_status "  curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s balanced"
            print_status "  curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s accurate"
            exit 1
            ;;
    esac
else
    # No configuration provided - interactive selection
    echo ""
    print_status "Choose your performance configuration:"
    echo "1) Fast (Default) - Single CLIP model, fastest indexing and retrieval"
    echo "2) Balanced - 4 models with balanced performance and accuracy"
    echo "3) Accurate - 6 models with highest accuracy but slower performance"
    echo ""

    # Check if we're being run from a file (interactive) vs piped (non-interactive)
    if [ -f "${BASH_SOURCE[0]}" ] && [ "${BASH_SOURCE[0]}" != "/dev/stdin" ]; then
        # Interactive mode - script is being run from a file
        echo -n "Enter your choice (1-3) [default: 1]: "
        read config_choice
    else
        # Non-interactive mode (piped from curl) - use default
        print_warning "Non-interactive mode detected. Using default configuration: fast"
        print_status "To choose a different configuration, run:"
        print_status "  curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s fast"
        print_status "  curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s balanced"
        print_status "  curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s accurate"
        print_status ""
        print_status "Or download and run interactively:"
        print_status "  curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh -o install-needle.sh"
        print_status "  bash install-needle.sh"
        config_choice="1"
    fi

    case $config_choice in
        1|"")
            CONFIG_MODE="fast"
            ;;
        2)
            CONFIG_MODE="balanced"
            ;;
        3)
            CONFIG_MODE="accurate"
            ;;
        *)
            print_error "Invalid choice. Using default: fast"
            CONFIG_MODE="fast"
            ;;
    esac
fi

print_success "Selected ${CONFIG_MODE} configuration"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
print_status "Using temporary directory: $TEMP_DIR"

# Clone repository with submodules
print_status "Cloning Needle repository with submodules..."
cd "$TEMP_DIR"
git clone --recursive https://github.com/UIC-InDeXLab/Needle.git
cd Needle

# Make install script executable and run it
print_status "Running Needle installer with ${CONFIG_MODE} configuration..."
chmod +x install.sh
./install.sh "$CONFIG_MODE"

# Move to user's home directory
INSTALL_DIR="$HOME/.needle"
if [ -d "$INSTALL_DIR" ]; then
    print_warning "Directory $INSTALL_DIR already exists. Removing old installation..."
    rm -rf "$INSTALL_DIR"
fi

print_status "Moving installation to $INSTALL_DIR..."
mv "$TEMP_DIR/Needle" "$INSTALL_DIR"

# Clean up temporary directory
rm -rf "$TEMP_DIR"

# Change to installation directory
cd "$INSTALL_DIR"

print_success "🎉 Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start services: cd $INSTALL_DIR && ./start-needle.sh"
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
echo "📊 Configuration: ${CONFIG_MODE}"
print_warning "Run 'cd $INSTALL_DIR && ./start-needle.sh' or 'needlectl service start' to start all services."
