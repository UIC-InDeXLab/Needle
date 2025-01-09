#!/usr/bin/env bash

set -euo pipefail

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Uninstalling Needle...${NC}"

# Identify the user to uninstall for
INSTALL_USER=${SUDO_USER:-$(whoami)}
INSTALL_HOME=$(eval echo "~${INSTALL_USER}")
NEEDLE_HOME_DIR="${INSTALL_HOME}/.needle"
NEEDLECTL_PATH="/usr/local/bin/needlectl"

# Detect OS and choose the correct shell config file
OS_TYPE="${OSTYPE}"
if [[ "$OS_TYPE" == "darwin"* ]]; then
    # macOS typically uses zsh by default
    SHELL_RC_FILE="${INSTALL_HOME}/.zshrc"
    echo -e "${YELLOW}Detected macOS. Will remove environment variables from ${SHELL_RC_FILE}.${NC}"
else
    SHELL_RC_FILE="${INSTALL_HOME}/.bashrc"
fi

### Step 1: Identify docker-compose file
COMPOSE_FILE_PATH="${NEEDLE_HOME_DIR}/docker-compose.yaml"
if [ ! -f "${COMPOSE_FILE_PATH}" ]; then
    echo -e "${YELLOW}No docker-compose.yaml found at ${COMPOSE_FILE_PATH}, services may already be down.${NC}"
fi

### Step 2: Bring down Docker services and remove volumes
if [ -f "${COMPOSE_FILE_PATH}" ]; then
    echo -e "${GREEN}Bringing down Needle services and removing volumes...${NC}"
    # Export NEEDLE_HOME temporarily if not set, to ensure docker-compose works
    export NEEDLE_HOME="${NEEDLE_HOME_DIR}"
    docker compose -f "${COMPOSE_FILE_PATH}" down -v || true
fi

### Step 3: Remove needlectl
if [ -f "${NEEDLECTL_PATH}" ]; then
    echo -e "${GREEN}Removing needlectl...${NC}"
    sudo rm -f "${NEEDLECTL_PATH}"
else
    echo -e "${YELLOW}needlectl not found at ${NEEDLECTL_PATH}, skipping removal.${NC}"
fi

### Step 4: Remove NEEDLE_HOME environment variable from shell config file
if sudo -u "${INSTALL_USER}" grep -q "^export NEEDLE_HOME=" "${SHELL_RC_FILE}" 2>/dev/null; then
    echo -e "${GREEN}Removing NEEDLE_HOME from ${SHELL_RC_FILE}...${NC}"
    # Use a backup-aware sed command for macOS (it requires a suffix for -i):
    sudo -u "${INSTALL_USER}" sed -i.bak "/^export NEEDLE_HOME=/d" "${SHELL_RC_FILE}" && sudo -u "${INSTALL_USER}" rm -f "${SHELL_RC_FILE}.bak"
else
    echo -e "${YELLOW}NEEDLE_HOME not set in ${SHELL_RC_FILE}, skipping.${NC}"
fi

### Step 5: Remove ~/.needle directory
if [ -d "${NEEDLE_HOME_DIR}" ]; then
    echo -e "${GREEN}Removing Needle home directory ${NEEDLE_HOME_DIR}...${NC}"
    sudo rm -rf "${NEEDLE_HOME_DIR}"
else
    echo -e "${YELLOW}${NEEDLE_HOME_DIR} not found, skipping removal.${NC}"
fi

### Step 6: (Optional) Clean up Docker images/volumes if desired
# echo -e "${GREEN}Cleaning up Docker images/volumes...${NC}"
# docker image prune -a -f
# docker volume prune -f

### Step 7: Final message
echo -e "${GREEN}Uninstallation complete!${NC}"
echo -e "${YELLOW}Note: You may want to restart your shell session to ensure all environment variables are cleared.${NC}"