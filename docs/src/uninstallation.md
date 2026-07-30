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

Your indexed data is **kept by default**. It lives in:

- `~/.needle` — source and CLI installs
- `~/Library/Application Support/com.needle.app` — the packaged macOS app
  (`~/.local/share/com.needle.app` on Linux)
- `~/.cache/huggingface` — downloaded model weights (several GB)

## Complete Cleanup

To also remove indexed data, vectors, saved credentials, and Needle's cached
models, run with `--purge`:

```bash
./scripts/uninstall.sh --purge
```

> Only Needle's own entries are removed from the HuggingFace cache, since that
> directory is shared with other tools that may rely on it.

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
rm -rf ~/Library/Application\ Support/com.needle.app   # macOS
rm -rf ~/.local/share/com.needle.app                   # Linux

# Remove downloaded models (optional, several GB)
rm -rf ~/.cache/huggingface
```

