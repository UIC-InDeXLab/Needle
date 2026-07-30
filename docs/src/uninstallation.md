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

- **The Needle desktop app** (`/Applications/Needle.app` on macOS; the installed
  package on Linux and Windows)

Your indexed data is **kept by default**. It lives in:

- `~/Library/Application Support/com.needle.app` — macOS
- `~/.local/share/com.needle.app` — Linux
- `%APPDATA%\com.needle.app` — Windows
- `~/.cache/huggingface` — downloaded model weights (several GB, shared with
  other Hugging Face tools)

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
sudo apt remove needle                     # Linux (.deb)
sudo dnf remove needle                     # Linux (.rpm)

# Remove all user data (optional)
rm -rf ~/Library/Application\ Support/com.needle.app   # macOS
rm -rf ~/.local/share/com.needle.app                   # Linux

# Remove downloaded models (optional, several GB)
rm -rf ~/.cache/huggingface
```

On Windows, uninstall Needle from **Settings → Apps**, then optionally delete
`%APPDATA%\com.needle.app` and `%USERPROFILE%\.cache\huggingface`.

> Deleting only the data directory (and keeping the Hugging Face cache) resets
> Needle to a first run without re-downloading several gigabytes of models.

