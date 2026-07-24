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

- **The Needle desktop app** (`/Applications/Needle.app` on macOS; the `.deb`
  package or `~/.local/bin/Needle.AppImage` on Linux)
- **needlectl binary** (from `/usr/local/bin` or `~/.local/bin`)

Your indexed data at `~/.needle` is **kept by default**.

## Complete Cleanup

To also remove all indexed data, vectors, saved credentials, and cached models
(`~/.needle`), run with `--purge`:

```bash
./scripts/uninstall.sh --purge
```

## Manual Cleanup

If you prefer to remove things by hand:

```bash
# Remove the app
rm -rf /Applications/Needle.app            # macOS
sudo dpkg -r needle                        # Linux (.deb)
rm -f ~/.local/bin/Needle.AppImage         # Linux (AppImage)

# Remove the CLI
sudo rm -f /usr/local/bin/needlectl ~/.local/bin/needlectl

# Remove all user data (optional)
rm -rf ~/.needle
```

