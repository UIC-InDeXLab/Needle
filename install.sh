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

### Step 1: Check Dependencies
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not installed. Please install Docker and re-run.${NC}"
    exit 1
fi

# Check docker compose plugin (docker compose v2)
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: docker compose plugin not installed. Please install and re-run.${NC}"
    exit 1
fi

echo -e "${GREEN}Docker and docker compose found.${NC}"

### Step 2: Check for GPU availability
HAS_GPU=false
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

### Step 3: Download appropriate docker-compose file
if [ "$HAS_GPU" = true ]; then
    COMPOSE_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/docker-compose.gpu.yaml"
    echo -e "${GREEN}Downloading GPU docker-compose configuration...${NC}"
else
    COMPOSE_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/docker-compose.cpu.yaml"
    echo -e "${GREEN}Downloading CPU docker-compose configuration...${NC}"
fi

mkdir -p "${NEEDLE_CONFIG_DIR}"
curl -fSL "${COMPOSE_URL}" -o "${NEEDLE_CONFIG_DIR}/docker-compose.yaml"
chown -R "${INSTALL_USER}:${INSTALL_USER}" "${NEEDLE_CONFIG_DIR}"
chmod -R u+rwX "${NEEDLE_CONFIG_DIR}"

echo -e "${GREEN}docker-compose file stored at ${NEEDLE_CONFIG_DIR}/docker-compose.yaml.${NC}"

### Step 4: Add user to docker group if not already
if ! groups "${INSTALL_USER}" | grep -q "\bdocker\b"; then
    echo -e "${GREEN}Adding ${INSTALL_USER} to docker group...${NC}"
    sudo usermod -aG docker "${INSTALL_USER}"
    echo -e "${YELLOW}User added to docker group. Please log out and log back in or run 'newgrp docker' to apply.${NC}"
fi

### Step 5: Download needlectl and make it accessible system-wide
NEEDLECTL_URL="https://github.com/UIC-InDeXLab/Needle/releases/download/v0.1.0/needlectl"
NEEDLECTL_PATH="/usr/local/bin/needlectl"

echo -e "${GREEN}Downloading needlectl tool...${NC}"
sudo curl -fSL "${NEEDLECTL_URL}" -o "${NEEDLECTL_PATH}"
sudo chmod +x "${NEEDLECTL_PATH}"

echo -e "${GREEN}needlectl installed at ${NEEDLECTL_PATH}.${NC}"

### Step 6: Configure the environment variable in user's .bashrc
BASHRC_FILE="${INSTALL_HOME}/.bashrc"
LINE_TO_ADD="export ${ENV_VAR}=\"${NEEDLE_CONFIG_DIR}/docker-compose.yaml\""

if ! sudo -u "${INSTALL_USER}" grep -q "^export ${ENV_VAR}=" "${BASHRC_FILE}" 2>/dev/null; then
    echo -e "${GREEN}Configuring ${ENV_VAR} in ${BASHRC_FILE}.${NC}"
    sudo -u "${INSTALL_USER}" bash -c "echo '${LINE_TO_ADD}' >> '${BASHRC_FILE}'"
else
    echo -e "${YELLOW}${ENV_VAR} is already set in ${BASHRC_FILE}, skipping.${NC}"
fi

### Step 7: Final message
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}You can now use 'needlectl' to manage the Needle environment.${NC}"
echo -e "${YELLOW}Run 'source ${BASHRC_FILE}' or open a new shell to ensure ${ENV_VAR} is set.${NC}"
echo -e "${YELLOW}Then run 'needlectl service start' to start Needle services.${NC}"
