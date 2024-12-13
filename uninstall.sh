#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Uninstalling Needle...${NC}"

# Identify the user who installed Needle. If run with sudo, $SUDO_USER may be set.
INSTALL_USER=${SUDO_USER:-$(whoami)}
INSTALL_HOME=$(eval echo "~${INSTALL_USER}")
NEEDLE_CONFIG_DIR="${INSTALL_HOME}/.needle"
NEEDLECTL_PATH="/usr/local/bin/needlectl"
ENV_FILE="/etc/environment"
ENV_VAR="NEEDLE_DOCKER_COMPOSE_FILE"

### Step 1: Identify docker-compose file from environment
COMPOSE_FILE_PATH=""
if [ -f "${ENV_FILE}" ]; then
    # Extract the docker-compose path if set
    COMPOSE_FILE_PATH=$(grep "^${ENV_VAR}=" "${ENV_FILE}" | cut -d'=' -f2 || true)
fi

# If not set in environment, try default ~/.needle/docker-compose.yaml
if [ -z "${COMPOSE_FILE_PATH}" ] || [ ! -f "${COMPOSE_FILE_PATH}" ]; then
    if [ -f "${NEEDLE_CONFIG_DIR}/docker-compose.yaml" ]; then
        COMPOSE_FILE_PATH="${NEEDLE_CONFIG_DIR}/docker-compose.yaml"
    fi
fi

### Step 2: Bring down Docker services
if [ -n "${COMPOSE_FILE_PATH}" ] && [ -f "${COMPOSE_FILE_PATH}" ]; then
    echo -e "${GREEN}Bringing down Needle services...${NC}"
    # Run as INSTALL_USER if that user is in docker group
    # If uninstalling as root, might need `sudo -u "${INSTALL_USER}"` if desired
    # Assuming `uninstall.sh` is run by the same user who installed or they have docker access:
    docker compose -f "${COMPOSE_FILE_PATH}" down || true
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
else
    echo -e "${YELLOW}${ENV_FILE} not found, skipping environment variable removal.${NC}"
fi

### Step 5: Remove ~/.needle directory
if [ -d "${NEEDLE_CONFIG_DIR}" ]; then
    echo -e "${GREEN}Removing configuration directory ${NEEDLE_CONFIG_DIR}...${NC}"
    rm -rf "${NEEDLE_CONFIG_DIR}"
else
    echo -e "${YELLOW}${NEEDLE_CONFIG_DIR} not found, skipping removal.${NC}"
fi

### (Optional) Step 6: Clean up Docker images/volumes (commented out)
# echo -e "${GREEN}Cleaning up Docker images/volumes...${NC}"
# Uncomment if you want to remove related Docker images/volumes:
# docker image prune -a -f
# docker volume prune -f

### Step 7: Final message
echo -e "${GREEN}Uninstallation complete!${NC}"
echo -e "If you re-install Needle in the future, you may need to run 'source /etc/environment' or log out and back in to ensure environment variables are updated."
