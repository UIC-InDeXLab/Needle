# Uninstallation

## Quick Uninstall

To uninstall Needle from your system, run:

```bash
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/uninstall.sh | bash
```

Or if you have the repository cloned:

```bash
./scripts/uninstall.sh
```

## What Gets Removed

By default, the uninstallation script removes:

- **Needle installation directory** (`~/.needle`)
- **needlectl binary** (from `/usr/local/bin` or `~/.local/bin`)
- **Virtual environments** for backend and ImageGeneratorsHub
- **Service management scripts**
- **Log files and PID files**

## Optional Cleanup

In interactive mode, you'll be prompted to optionally remove:

- **Docker volumes** - Contains indexed data and images (not removed by default)

## Complete Cleanup

To completely remove all Needle data including Docker volumes:

```bash
# Run uninstall script and choose to remove Docker volumes when prompted
./scripts/uninstall.sh

# Additionally, remove Docker images
docker system prune -a
```

## Manual Cleanup

If the automatic uninstall fails (e.g., due to permission issues with Docker volumes), you can manually clean up:

```bash
# Stop any running services first
needlectl service stop 2>/dev/null || true

# Remove Docker containers and volumes
docker compose -f ~/.needle/docker/docker-compose.infrastructure.yaml down -v 2>/dev/null || true

# Remove the installation directory (may need sudo for Docker volume files)
sudo rm -rf ~/.needle

# Remove needlectl binary
sudo rm -f /usr/local/bin/needlectl
rm -f ~/.local/bin/needlectl

# Clean up Docker images (optional)
docker system prune -a
```
