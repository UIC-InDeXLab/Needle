# Getting Started

## Prerequisites

Before installing Needle, ensure that you have the following prerequisites installed:

- **Docker:** Needle relies on Docker to containerize its infrastructure services.  
  [Install Docker](https://docs.docker.com/get-docker/)

- **Docker Compose:** This tool is required to orchestrate the multi-container setup.  
  [Install Docker Compose](https://docs.docker.com/compose/install/)

- **Python 3.8+:** Required for the backend and image generator services (Python 3.12+ recommended).  
  [Install Python](https://www.python.org/downloads/)

- **Git:** Required for cloning the repository and managing updates.  
  [Install Git](https://git-scm.com/downloads)

> **Warning:** Make sure your user account is added to the Docker group so you can run Docker commands (e.g., `docker ps`) without needing root privileges.

> **Note:** Currently, Needle is supported on **Linux** and **macOS**.

## Installation

### Quick Install (Recommended)

Install Needle with a single command - no cloning required:

```bash
# Default installation (fast mode - recommended for getting started)
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/install-oneliner.sh | bash

# Or with a specific configuration mode
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/install-oneliner.sh | bash -s fast
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/install-oneliner.sh | bash -s balanced
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/install-oneliner.sh | bash -s accurate
```

This installs Needle to `~/.needle` and adds the `needlectl` command-line tool.

### Configuration Options

Choose your performance configuration:

- **Fast (Default):** Single CLIP model, fastest indexing and retrieval - best for getting started quickly
- **Balanced:** 4 models with balanced performance and accuracy
- **Accurate:** 6 models with highest accuracy but slower performance

> **Warning:** Once the configuration mode is set, it cannot be changed without uninstalling and reinstalling Needle, which will result in data loss.

> **Note:** Needle automatically checks for GPU accessibility and will use the GPU if available to optimize performance.

### What Gets Installed

The installation process sets up:

- **Virtual Environments:** Separate Python environments for backend and image generator services
- **Docker Infrastructure:** PostgreSQL, Milvus, MinIO, and etcd services via Docker Compose
- **Configuration Files:** Performance-optimized settings based on your chosen mode
- **needlectl CLI:** Command-line interface for managing Needle (installed to `/usr/local/bin/needlectl`)

## Starting the Needle Service

Once installed, start the Needle service by running:

```bash
needlectl service start
```

This command will start all the necessary infrastructure services (PostgreSQL, Milvus, etc.) and the Needle backend.

To verify that everything is running as expected, check the service status:

```bash
needlectl service status
```

And confirm the installed version using:

```bash
needlectl --version
```

### Access Points

After starting services, you can access:

- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Image Generator:** http://localhost:8010

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
