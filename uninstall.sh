#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

INSTALL_DIR="/opt/needle"
NEEDLECTL_PATH="/usr/local/bin/needlectl"
ENV_FILE="/etc/environment"
ENV_VAR="NEEDLE_DOCKER_COMPOSE_FILE"
COMPOSE_FILE_PATH=""

echo -e "${GREEN}Uninstalling Needle...${NC}"

### Step 1: Identify docker-compose file
if [ -f "${ENV_FILE}" ]; then
    # Extract the docker-compose path if set
    COMPOSE_FILE_PATH=$(grep "^${ENV_VAR}=" "${ENV_FILE}" | cut -d'=' -f2 || true)
fi

if [ -z "${COMPOSE_FILE_PATH}" ] || [ ! -f "${COMPOSE_FILE_PATH}" ]; then
    # If we didn't find it in /etc/environment, check default
    if [ -f "${INSTALL_DIR}/docker-compose.yaml" ]; then
        COMPOSE_FILE_PATH="${INSTALL_DIR}/docker-compose.yaml"
    fi
fi

### Step 2: Bring down Docker services
if [ -n "${COMPOSE_FILE_PATH}" ] && [ -f "${COMPOSE_FILE_PATH}" ]; then
    echo -e "${GREEN}Bringing down Needle services...${NC}"
    pushd "$(dirname "${COMPOSE_FILE_PATH}")" > /dev/null
    sudo docker-compose -f "${COMPOSE_FILE_PATH}" down
    popd > /dev/null
else
    echo -e "${YELLOW}Warning: Could not find docker-compose.yaml. Services may already be down.${NC}"
fi

### Step 3: Remove needlectl
if [ -f "${NEEDLECTL_PATH}" ]; then
    echo -e "${GREEN}Removing needlectl...${NC}"
    sudo rm -f "${NEEDLECTL_PATH}"
else
    echo -e "${YELLOW}needlectl not found at ${NEEDLECTL_PATH}, skipping removal.${NC}"
fi

### Step 4: Remove environment variable from /etc/environment
if [ -f "${ENV_FILE}" ]; then
    if grep -q "^${ENV_VAR}=" "${ENV_FILE}"; then
        echo -e "${GREEN}Removing ${ENV_VAR} from ${ENV_FILE}...${NC}"
        sudo sed -i "/^${ENV_VAR}=/d" "${ENV_FILE}"
    else
        echo -e "${YELLOW}${ENV_VAR} not set in ${ENV_FILE}, skipping.${NC}"
    fi
fi

### Step 5: Remove application directory
if [ -d "${INSTALL_DIR}" ]; then
    echo -e "${GREEN}Removing installation directory ${INSTALL_DIR}...${NC}"
    sudo rm -rf "${INSTALL_DIR}"
else
    echo -e "${YELLOW}Installation directory ${INSTALL_DIR} not found, skipping removal.${NC}"
fi

### (Optional) Step 6: Clean up Docker images/volumes (commented out)
# echo -e "${GREEN}Cleaning up Docker images/volumes...${NC}"
# To remove associated images or volumes, uncomment below commands:
# sudo docker image prune -a -f
# sudo docker volume prune -f

### Step 7: Final message
echo -e "${GREEN}Uninstallation complete!${NC}"
echo -e "If you re-install Needle in the future, you may need to run 'source /etc/environment' or log out and back in to ensure environment variables are updated."
