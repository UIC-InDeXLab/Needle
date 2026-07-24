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

## Installation

### Option A — Download an installer (recommended)

Download the installer for your platform from the
[releases page](https://github.com/UIC-InDeXLab/Needle/releases):

- **macOS:** `Needle_x.y.z.dmg` — open it and drag Needle to Applications.
- **Linux:** `Needle_x.y.z.deb` (`sudo dpkg -i Needle_*.deb`) or `Needle_x.y.z.AppImage`
  (`chmod +x` and run).

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

- **fast** (default): single model, fastest indexing/retrieval.
- **balanced**: 4 models, balanced accuracy.
- **accurate**: 6 models, best accuracy (slower).

> **Note:** Needle automatically uses your GPU (CUDA) or Apple Silicon (MPS) when available.

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
