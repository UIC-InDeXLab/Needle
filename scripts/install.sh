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
NEEDLE_CONFIG_DIR="${INSTALL_HOME}/.needle"
ENV_VAR="NEEDLE_DOCKER_COMPOSE_FILE"

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

### Step 3: Download appropriate docker-compose file
if [ "$HAS_GPU" = true ]; then
    COMPOSE_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/docker/docker-compose.gpu.yaml"
    echo -e "${GREEN}Downloading GPU docker-compose configuration...${NC}"
else
    COMPOSE_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/docker/docker-compose.cpu.yaml"
    echo -e "${GREEN}Downloading CPU docker-compose configuration...${NC}"
fi

mkdir -p "${NEEDLE_CONFIG_DIR}"
curl -fSL "${COMPOSE_URL}" -o "${NEEDLE_CONFIG_DIR}/docker-compose.yaml"
chown -R "${INSTALL_USER}:${INSTALL_USER}" "${NEEDLE_CONFIG_DIR}"
chmod -R u+rwX "${NEEDLE_CONFIG_DIR}"

echo -e "${GREEN}docker-compose file stored at ${NEEDLE_CONFIG_DIR}/docker-compose.yaml.${NC}"

### Step 4: Add user to docker group if not already (Skip for macOS)
if [[ "$OS_TYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}On macOS, Docker Desktop does not require adding the user to a 'docker' group.${NC}"
else
    if ! groups "${INSTALL_USER}" | grep -q "\bdocker\b"; then
        echo -e "${GREEN}Adding ${INSTALL_USER} to docker group...${NC}"
        sudo usermod -aG docker "${INSTALL_USER}"
        echo -e "${YELLOW}User added to docker group. Please log out and log back in or run 'newgrp docker' to apply.${NC}"
    fi
fi

### Step 5: Download needlectl and make it accessible system-wide
NEEDLECTL_URL="https://github.com/UIC-InDeXLab/Needle/releases/download/latest/needlectl"
NEEDLECTL_PATH="/usr/local/bin/needlectl"

echo -e "${GREEN}Downloading needlectl tool...${NC}"
sudo curl -fSL "${NEEDLECTL_URL}" -o "${NEEDLECTL_PATH}"
sudo chmod +x "${NEEDLECTL_PATH}"

echo -e "${GREEN}needlectl installed at ${NEEDLECTL_PATH}.${NC}"

### Step 6: Configure the environment variable in user's shell file
LINE_TO_ADD="export ${ENV_VAR}=\"${NEEDLE_CONFIG_DIR}/docker-compose.yaml\""

if ! sudo -u "${INSTALL_USER}" grep -q "^export ${ENV_VAR}=" "${SHELL_RC_FILE}" 2>/dev/null; then
    echo -e "${GREEN}Configuring ${ENV_VAR} in ${SHELL_RC_FILE}.${NC}"
    sudo -u "${INSTALL_USER}" bash -c "echo '${LINE_TO_ADD}' >> '${SHELL_RC_FILE}'"
else
    echo -e "${YELLOW}${ENV_VAR} is already set in ${SHELL_RC_FILE}, skipping.${NC}"
fi

### Step 7: Final message
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}You can now use 'needlectl' to manage the Needle environment.${NC}"
echo -e "${YELLOW}Run 'source ${SHELL_RC_FILE}' or open a new shell to ensure ${ENV_VAR} is set.${NC}"
echo -e "${YELLOW}Then run 'needlectl service start' to start Needle services.${NC}"
echo -e "${YELLOW}On macOS, ensure Docker Desktop is running before using 'needlectl'.${NC}"
