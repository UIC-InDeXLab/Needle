# Getting Started

## Prerequisites

Needle is a self-contained desktop application. **End users do not need Docker,
PostgreSQL, or any external services** — everything (metadata via SQLite, vectors
via LanceDB, and on-device image generation) runs locally inside the app.

To **build** Needle from source you need:

- **Python 3.12+** — for the bundled backend. [Install Python](https://www.python.org/downloads/)
- **Node.js 18+** — for the UI. [Install Node.js](https://nodejs.org/)
- **Rust toolchain** — for the Tauri desktop shell. [Install Rust](https://rustup.rs/)

> **Note:** Needle is supported on **Linux** and **macOS**.
>
> On macOS, Needle requires **macOS 14 (Sonoma) or later** on an **Apple Silicon**
> Mac. Intel Macs are not supported: PyTorch stopped publishing macOS x86_64
> builds after 2.2, so the bundled backend cannot be built for them.

## Installation

### Option A — Download an installer (recommended)

Download the installer for your platform from the
[releases page](https://github.com/UIC-InDeXLab/Needle/releases):

- **macOS:** `Needle_x.y.z_macos_arm64.dmg` — open it and drag Needle to
  Applications, then see [Opening Needle on macOS](#opening-needle-on-macos) below.
- **Linux:** `Needle_x.y.z.deb` (`sudo dpkg -i Needle_*.deb`) or `Needle_x.y.z.AppImage`
  (`chmod +x` and run).

Each release also ships a `.sha256` file so you can verify the download:

```bash
shasum -a 256 -c Needle_*_macos_arm64.dmg.sha256
```

### Opening Needle on macOS

The released app is **not signed with an Apple Developer ID**, because signing
and notarization require a paid Apple Developer account. The first time you open
it, macOS will refuse and show something like:

> **"Needle is damaged and can't be opened. You should move it to the Bin."**

**The app is not damaged.** That wording is what macOS shows for any app it
cannot attribute to a registered developer. When you download a file, your
browser attaches a `com.apple.quarantine` flag to it; Gatekeeper checks that
flagged apps are both signed by a known developer and notarized by Apple, and
Needle is neither.

To open it, remove the quarantine flag once:

```bash
xattr -dr com.apple.quarantine /Applications/Needle.app
```

Then launch Needle normally. You only need to do this once per install.

> **Why not just right-click → Open?** That shortcut no longer works for
> unsigned apps on recent macOS versions. Removing the quarantine attribute (or
> approving the app under **System Settings → Privacy & Security** after a
> blocked launch attempt) is the supported route.

If you would rather not run that command, build from source instead — apps you
build locally are never quarantined, so they open with no extra steps.

### Option B — Build & install from source

```bash
git clone https://github.com/UIC-InDeXLab/Needle.git
cd Needle
./scripts/install.sh            # or: fast | balanced | accurate
```

This builds the desktop app (with a bundled backend) and the `needlectl` CLI,
then installs both. Your data is stored in `~/.needle/data`.

### Configuration modes

Pass a mode to `install.sh` to control accuracy vs. speed:

- **fast** (default): 2 lightweight models, fastest indexing/retrieval.
- **balanced**: 4 models, balanced accuracy.
- **accurate**: 6 models, best accuracy (slower).

You can also pick the mode in the app's welcome screen on first launch.

### First launch

The first time you open Needle it downloads the models for the mode you chose
(roughly 3.7 GB for **fast**) and shows live progress. Models are cached in
`~/.cache/huggingface`, so later launches start quickly.

> **Note:** Needle automatically uses your GPU (CUDA) or Apple Silicon (MPS) when
> available. It is enabled by default, and you can turn it on or off later under
> **Status → Hardware acceleration**; switching reloads the models but does not
> re-download them.

## Verifying the installation

Confirm the CLI is installed:

```bash
needlectl --version
```

### Access Points

The app starts its backend automatically on launch. When running, you can access:

- **Backend API:** http://127.0.0.1:8000
- **API Documentation:** http://127.0.0.1:8000/docs

## Managing Services

Use `needlectl` to manage all services:

```bash
# Start all services
needlectl service start

# Stop all services
needlectl service stop

# Check status
needlectl service status

# View logs
needlectl service log backend
needlectl service log image-generator-hub
needlectl service log infrastructure

# Restart services
needlectl service restart
```

## About needlectl

The `needlectl` command-line tool is the primary interface for interacting with Needle. It will be discussed in detail in the subsequent sections, where you'll learn how to leverage its full capabilities.
