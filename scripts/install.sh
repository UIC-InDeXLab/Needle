#!/usr/bin/env bash

set -euo pipefail

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Needle Installation...${NC}"

# Identify the user to install for (the one who invoked sudo)
INSTALL_USER=${SUDO_USER:-$(whoami)}
INSTALL_HOME=$(eval echo "~${INSTALL_USER}")
NEEDLE_HOME_DIR="${INSTALL_HOME}/.needle"

# Detect OS
OS_TYPE="${OSTYPE}"
if [[ "$OS_TYPE" == "darwin"* ]]; then
    # macOS typically uses zsh by default
    SHELL_RC_FILE="${INSTALL_HOME}/.zshrc"
    echo -e "${YELLOW}Detected macOS. Will configure environment variables in ${SHELL_RC_FILE}.${NC}"
else
    SHELL_RC_FILE="${INSTALL_HOME}/.bashrc"
fi

### Step 1: Check Dependencies
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not installed. Please install Docker (e.g., Docker Desktop) and re-run.${NC}"
    exit 1
fi

# Check docker compose plugin (docker compose v2)
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: docker compose plugin not installed. Please install and re-run.${NC}"
    exit 1
fi

echo -e "${GREEN}Docker and docker compose found.${NC}"

### Step 2: Check for GPU availability (skip on macOS)
HAS_GPU=false
if [[ "$OS_TYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}On macOS, GPU checks are skipped. Using CPU mode.${NC}"
    HAS_GPU=false
else
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}nvidia-smi found, checking Docker GPU access...${NC}"
        if docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi &> /dev/null; then
            echo -e "${GREEN}Docker GPU support detected.${NC}"
            HAS_GPU=true
        else
            echo -e "${YELLOW}GPU detected but Docker GPU access not possible. Falling back to CPU mode.${NC}"
        fi
    else
        echo -e "${YELLOW}No GPU detected, using CPU mode.${NC}"
    fi
fi

### Step 3: Select Database Mode
echo -e "${GREEN}Please select your preferred database mode:${NC}"
echo "1) Fast     - Focuses on low latency and fast indexing"
echo "2) Balanced - Balance between speed and accuracy"
echo "3) Accurate - Focuses on higher query retrieval accuracy"

while true; do
    read -p "Enter your choice (1-3): " mode_choice
    case $mode_choice in
        1)
            MODE="fast"
            break
            ;;
        2)
            MODE="balanced"
            break
            ;;
        3)
            MODE="accurate"
            break
            ;;
        *)
            echo -e "${RED}Invalid choice. Please enter 1, 2, or 3.${NC}"
            ;;
    esac
done

echo -e "${GREEN}Selected ${MODE} mode.${NC}"

### Step 4: Download appropriate docker-compose file and configs
if [ "$HAS_GPU" = true ]; then
    COMPOSE_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/docker/docker-compose.gpu.yaml"
    echo -e "${GREEN}Downloading GPU docker-compose configuration...${NC}"
else
    COMPOSE_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/docker/docker-compose.cpu.yaml"
    echo -e "${GREEN}Downloading CPU docker-compose configuration...${NC}"
fi

# Create necessary directories
mkdir -p "${NEEDLE_HOME_DIR}/configs"

# Download docker-compose file
curl -fSL "${COMPOSE_URL}" -o "${NEEDLE_HOME_DIR}/docker-compose.yaml"

# Download configuration files for selected mode
echo -e "${GREEN}Downloading configuration files for ${MODE} mode...${NC}"
CONFIG_BASE_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/configs/${MODE}"
CONFIG_FILES=("service.env" "directory.env" "query.env" "embedders.json")

for config_file in "${CONFIG_FILES[@]}"; do
    echo -e "${GREEN}Downloading ${config_file}...${NC}"
    curl -fSL "${CONFIG_BASE_URL}/${config_file}" -o "${NEEDLE_HOME_DIR}/configs/${config_file}"
done

# Set proper permissions
chown -R "${INSTALL_USER}:${INSTALL_USER}" "${NEEDLE_HOME_DIR}"
chmod -R u+rwX "${NEEDLE_HOME_DIR}"

echo -e "${GREEN}Configuration files stored in ${NEEDLE_HOME_DIR}/configs${NC}"

### Step 5: Add user to docker group if not already (Skip for macOS)
if [[ "$OS_TYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}On macOS, Docker Desktop does not require adding the user to a 'docker' group.${NC}"
else
    if ! groups "${INSTALL_USER}" | grep -q "\bdocker\b"; then
        echo -e "${GREEN}Adding ${INSTALL_USER} to docker group...${NC}"
        sudo usermod -aG docker "${INSTALL_USER}"
        echo -e "${YELLOW}User added to docker group. Please log out and log back in or run 'newgrp docker' to apply.${NC}"
    fi
fi

### Step 6: Download needlectl and make it accessible system-wide
NEEDLECTL_URL="https://github.com/UIC-InDeXLab/Needle/releases/download/latest/needlectl"
NEEDLECTL_PATH="/usr/local/bin/needlectl"

echo -e "${GREEN}Downloading needlectl tool...${NC}"
sudo curl -fSL "${NEEDLECTL_URL}" -o "${NEEDLECTL_PATH}"
sudo chmod +x "${NEEDLECTL_PATH}"

echo -e "${GREEN}needlectl installed at ${NEEDLECTL_PATH}.${NC}"

### Step 7: Configure NEEDLE_HOME in user's shell file
NEEDLE_HOME_VAR="export NEEDLE_HOME=\"${NEEDLE_HOME_DIR}\""

if ! sudo -u "${INSTALL_USER}" grep -q "^export NEEDLE_HOME=" "${SHELL_RC_FILE}" 2>/dev/null; then
    echo -e "${GREEN}Configuring NEEDLE_HOME in ${SHELL_RC_FILE}.${NC}"
    sudo -u "${INSTALL_USER}" bash -c "echo '${NEEDLE_HOME_VAR}' >> '${SHELL_RC_FILE}'"
fi

### Step 8: Final message
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}You can now use 'needlectl' to manage the Needle environment.${NC}"
echo -e "${YELLOW}Selected mode: ${MODE}${NC}"
echo -e "${YELLOW}NEEDLE_HOME has been set to: ${NEEDLE_HOME_DIR}${NC}"
echo -e "${YELLOW}Run 'source ${SHELL_RC_FILE}' or open a new shell to ensure NEEDLE_HOME is set.${NC}"
echo -e "${YELLOW}Then run 'needlectl service start' to start Needle services.${NC}"
echo -e "${YELLOW}On macOS, ensure Docker Desktop is running before using 'needlectl'.${NC}"
