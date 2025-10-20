#!/bin/bash

# Test script to verify Needle installation
# This script tests the unified installation system

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo -e "${GREEN}🧪 Testing Needle Installation${NC}"
echo "================================="

# Test 1: Check if install script exists and is executable
print_status "Testing install script..."
if [ -f "scripts/install.sh" ] && [ -x "scripts/install.sh" ]; then
    print_success "Install script exists and is executable"
else
    print_error "Install script missing or not executable"
    exit 1
fi

# Test 2: Check if uninstall script exists and is executable
print_status "Testing uninstall script..."
if [ -f "scripts/uninstall.sh" ] && [ -x "scripts/uninstall.sh" ]; then
    print_success "Uninstall script exists and is executable"
else
    print_error "Uninstall script missing or not executable"
    exit 1
fi

# Test 3: Check if infrastructure docker-compose exists
print_status "Testing infrastructure docker-compose..."
if [ -f "docker/docker-compose.infrastructure.yaml" ]; then
    print_success "Infrastructure docker-compose exists"
else
    print_error "Infrastructure docker-compose missing"
    exit 1
fi

# Test 4: Check if Makefile has correct targets
print_status "Testing Makefile targets..."
if grep -q "install:" Makefile && grep -q "start:" Makefile && grep -q "stop:" Makefile; then
    print_success "Makefile has required targets"
else
    print_error "Makefile missing required targets"
    exit 1
fi

# Test 5: Check if backend requirements.txt exists
print_status "Testing backend requirements..."
if [ -f "backend/requirements.txt" ]; then
    print_success "Backend requirements.txt exists"
else
    print_error "Backend requirements.txt missing"
    exit 1
fi

# Test 6: Check if configs directory exists
print_status "Testing configs directory..."
if [ -d "configs" ]; then
    print_success "Configs directory exists"
else
    print_error "Configs directory missing"
    exit 1
fi

# Test 7: Check if old scripts are removed
print_status "Testing old scripts removal..."
OLD_SCRIPTS=("setup-needle.sh" "setup-venv-needle.sh" "start-needle-venv.sh" "stop-needle-venv.sh" "status-needle-venv.sh")
MISSING_OLD_SCRIPTS=0
for script in "${OLD_SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        MISSING_OLD_SCRIPTS=$((MISSING_OLD_SCRIPTS + 1))
    fi
done

if [ $MISSING_OLD_SCRIPTS -eq ${#OLD_SCRIPTS[@]} ]; then
    print_success "All old scripts have been removed"
else
    print_warning "Some old scripts still exist"
fi

# Test 8: Check if ImageGeneratorsHub directory exists (or will be created)
print_status "Testing ImageGeneratorsHub setup..."
if [ -d "../ImageGeneratorsHub" ]; then
    print_success "ImageGeneratorsHub directory exists"
else
    print_warning "ImageGeneratorsHub directory not found (will be created during installation)"
fi

# Test 9: Check if one-liner script exists
print_status "Testing one-liner installation script..."
if [ -f "install-oneliner.sh" ] && [ -x "install-oneliner.sh" ]; then
    print_success "One-liner installation script exists and is executable"
else
    print_error "One-liner installation script missing or not executable"
    exit 1
fi

# Test 10: Check if configuration directories exist
print_status "Testing configuration directories..."
CONFIG_MODES=("fast" "balanced" "accurate")
for mode in "${CONFIG_MODES[@]}"; do
    if [ -d "configs/${mode}" ]; then
        print_success "Configuration directory configs/${mode} exists"
    else
        print_error "Configuration directory configs/${mode} missing"
        exit 1
    fi
done

print_success "🎉 All tests passed!"
echo ""
echo "📋 Installation is ready. To install Needle:"
echo "  One-liner: curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash"
echo "  Manual:    ./scripts/install.sh"
echo "  Fast mode: ./scripts/install.sh fast"
echo "  Balanced:  ./scripts/install.sh balanced"
echo "  Accurate:  ./scripts/install.sh accurate"
echo ""
echo "📋 To test the installation:"
echo "  make install"
echo "  make start"
echo "  make status"
