#!/bin/bash

# Test needlectl functionality
# This script tests the needlectl command after installation

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

echo -e "${GREEN}🧪 Testing needlectl Functionality${NC}"
echo "====================================="

# Test 1: Check if needlectl can be run
print_status "Testing needlectl help command..."
if source backend/venv/bin/activate && python3 needlectl/needlectl.py --help > /dev/null 2>&1; then
    print_success "needlectl help command works"
else
    print_error "needlectl help command failed"
    exit 1
fi

# Test 2: Check service commands
print_status "Testing needlectl service commands..."
if source backend/venv/bin/activate && python3 needlectl/needlectl.py service --help > /dev/null 2>&1; then
    print_success "needlectl service commands work"
else
    print_error "needlectl service commands failed"
    exit 1
fi

# Test 3: Check status command
print_status "Testing needlectl service status..."
if source backend/venv/bin/activate && python3 needlectl/needlectl.py service status > /dev/null 2>&1; then
    print_success "needlectl service status works"
else
    print_error "needlectl service status failed"
    exit 1
fi

# Test 4: Check if infrastructure services are running
print_status "Testing infrastructure services status..."
if source backend/venv/bin/activate && python3 needlectl/needlectl.py service status | grep -q "milvus-standalone"; then
    print_success "Infrastructure services are accessible"
else
    print_warning "Infrastructure services may not be running"
fi

# Test 5: Check if virtual environment services are detected
print_status "Testing virtual environment services detection..."
if source backend/venv/bin/activate && python3 needlectl/needlectl.py service status | grep -q "virtual_env_services"; then
    print_success "Virtual environment services are detected"
else
    print_error "Virtual environment services detection failed"
    exit 1
fi

print_success "🎉 All needlectl tests passed!"
echo ""
echo "📋 needlectl is working correctly. You can now use:"
echo "  - needlectl service start"
echo "  - needlectl service stop"
echo "  - needlectl service status"
echo "  - needlectl service log [service]"
echo ""
echo "📋 To install needlectl system-wide, run the installation script:"
echo "  ./scripts/install.sh"
