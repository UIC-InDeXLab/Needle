#!/usr/bin/env bash

set -euo pipefail

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Needle Installation...${NC}"

### Step 1: Check Dependencies

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker not installed. Please install Docker and re-run.${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Error: docker compose not installed. Please install docker compose and re-run.${NC}"
    exit 1
fi

echo -e "${GREEN}Docker and docker compose found.${NC}"

### Step 2: Check for GPU availability

HAS_GPU=false

# Check if nvidia-smi is available (indicates a CUDA GPU)
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}nvidia-smi found, checking Docker GPU access...${NC}"
    # Test if Docker can run GPU-enabled containers
    if docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi &> /dev/null; then
        echo -e "${GREEN}Docker GPU support detected.${NC}"
        HAS_GPU=true
    else
        echo -e "${YELLOW}nvidia-smi is available but Docker can't access GPU. Falling back to CPU mode.${NC}"
    fi
else
    echo -e "${YELLOW}No GPU detected or nvidia-smi not available. Using CPU mode.${NC}"
fi

### Step 3: Download appropriate docker-compose file

INSTALL_DIR="/opt/needle"
COMPOSE_FILE="docker-compose.yaml"

# Ensure INSTALL_DIR exists
sudo mkdir -p "${INSTALL_DIR}"

if [ "$HAS_GPU" = true ]; then
    COMPOSE_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/docker-compose.gpu.yaml"
    echo -e "${GREEN}Downloading GPU docker-compose configuration...${NC}"
else
    COMPOSE_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/docker-compose.cpu.yaml"
    echo -e "${GREEN}Downloading CPU docker-compose configuration...${NC}"
fi

# Download docker-compose file
sudo curl -fSL "${COMPOSE_URL}" -o "${INSTALL_DIR}/${COMPOSE_FILE}"
sudo chown root:root "${INSTALL_DIR}/${COMPOSE_FILE}"
sudo chmod 644 "${INSTALL_DIR}/${COMPOSE_FILE}"

echo -e "${GREEN}docker-compose file stored at ${INSTALL_DIR}/${COMPOSE_FILE}.${NC}"

### Step 4: Run docker-compose to start services

echo -e "${GREEN}Starting Needle stack with docker-compose...${NC}"
pushd "${INSTALL_DIR}" > /dev/null
sudo docker-compose -f "${COMPOSE_FILE}" up -d
popd > /dev/null
echo -e "${GREEN}Needle services started.${NC}"

### Step 5: Download needlectl and make it accessible

NEEDLECTL_URL="https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/cli/needlectl"
NEEDLECTL_PATH="/usr/local/bin/needlectl"

echo -e "${GREEN}Downloading needlectl tool...${NC}"
sudo curl -fSL "${NEEDLECTL_URL}" -o "${NEEDLECTL_PATH}"
sudo chmod +x "${NEEDLECTL_PATH}"

echo -e "${GREEN}needlectl installed at ${NEEDLECTL_PATH}.${NC}"

### Step 6: Enhance usability

# We can store the location of the docker-compose file inside needlectl using an environment variable
# Option: The script could write a config file that needlectl reads from, but since the instructions say
# "when user works with needlectl, it has access to the docker-compose path (predefined)",
# we can assume needlectl will check for a known ENV variable. We'll add it to /etc/environment for system-wide use.

ENV_FILE="/etc/environment"
ENV_VAR="NEEDLE_DOCKER_COMPOSE_FILE"
if grep -q "^${ENV_VAR}" "${ENV_FILE}" &>/dev/null; then
    sudo sed -i "s|^${ENV_VAR}.*|${ENV_VAR}=${INSTALL_DIR}/${COMPOSE_FILE}|" "${ENV_FILE}"
else
    echo "${ENV_VAR}=${INSTALL_DIR}/${COMPOSE_FILE}" | sudo tee -a "${ENV_FILE}" > /dev/null
fi

echo -e "${GREEN}Configured ${ENV_VAR} in ${ENV_FILE}.${NC}"
echo -e "${GREEN}Reload your shell or source /etc/environment to ensure needlectl uses the correct docker-compose file.${NC}"

### Step 7: Final message
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}You can now use 'needlectl' to manage the Needle environment.${NC}"
