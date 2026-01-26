# Uninstallation

If you decide to remove Needle from your system, you have several options depending on how you installed it.

## Quick Uninstall (One-Liner)

For installations done via the one-liner (located at `~/.needle`):

```bash
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/uninstall.sh | bash
```

> **Note:** When run non-interactively (piped from curl), the uninstall script will preserve your data (Docker volumes, ImageGeneratorsHub directory). To fully remove all data, run the uninstall script interactively.

## Interactive Uninstall (Recommended)

For more control over what gets removed, download and run the script interactively:

```bash
# For one-liner installations
cd ~/.needle
./scripts/uninstall.sh

# For manual installations
cd /path/to/Needle
./scripts/uninstall.sh
```

The interactive uninstall will prompt you to:
- Remove the ImageGeneratorsHub directory
- Remove Docker volumes (contains your indexed data)
- Remove the entire Needle directory (for one-liner installations)

## Using Make

If you installed manually and have the Makefile available:

```bash
cd /path/to/Needle
make uninstall
```

## What Gets Removed

The uninstallation process removes:

- **Virtual Environments:** Backend (`backend/venv`) and ImageGeneratorsHub (`.venv`) environments
- **Service Management Scripts:** `start-needle.sh`, `stop-needle.sh`, `status-needle.sh`
- **needlectl Binary:** Removes `/usr/local/bin/needlectl`
- **Log Files:** All log files in the `logs/` directory
- **PID Files:** Process ID files used for service management

## What Gets Preserved (By Default)

Unless you explicitly choose to remove them:

- **Source Code:** The Needle repository files remain intact
- **Docker Images:** Cached Docker images are preserved (saves time on reinstall)
- **Docker Volumes:** Your indexed data is preserved
- **ImageGeneratorsHub Directory:** The image generator models are preserved

## Complete Cleanup

To completely remove all Needle-related data:

1. **Run the uninstall script interactively and select "yes" for all prompts**

2. **Remove Docker images:**

```bash
docker system prune -a
```

3. **Remove any remaining Docker volumes:**

```bash
docker volume prune
```

## Reinstallation

After uninstalling, you can reinstall Needle at any time:

```bash
# One-liner installation
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/install-oneliner.sh | bash

# Or manual installation
git clone --recursive https://github.com/UIC-InDeXLab/Needle.git
cd Needle
./scripts/install.sh
```
