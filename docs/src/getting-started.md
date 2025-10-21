# Getting Started

## Prerequisites

Before installing Needle, ensure that you have the following prerequisites installed:

- **Docker:** Needle relies on Docker to containerize its infrastructure services.  
  [Install Docker](https://docs.docker.com/get-docker/)

- **Docker Compose:** This tool is required to orchestrate the multi-container setup.  
  [Install Docker Compose](https://docs.docker.com/compose/install/)

- **Python 3.8+:** Required for the backend and image generator services.  
  [Install Python](https://www.python.org/downloads/)

- **Git:** Required for cloning the repository and managing updates.  
  [Install Git](https://git-scm.com/downloads)

> **Warning:** Make sure your user account is added to the Docker group so you can run Docker commands (e.g., `docker ps`) without needing root privileges.

> **Note:** Currently, Needle is supported on **Linux** and **macOS**.

## Installation

### Quick Install (Recommended)

To install Needle, run the following one-liner in your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/install.sh -o install.sh && bash install.sh && rm install.sh
```

### Manual Installation

If you prefer to install manually or need more control over the process:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/UIC-IndexLab/Needle.git
   cd Needle
   ```

2. **Run the installation script:**
   ```bash
   ./scripts/install.sh
   ```

### Configuration Options

During the installation process, you will be prompted to choose the database mode. The available options are:

- **Fast:** Offers quick responses and indexing with lower accuracy.
- **Balanced:** Provides a compromise between speed and accuracy.
- **Accurate:** Prioritizes high accuracy, which may come at the cost of slower performance.

> **Warning:** Once the database mode is set, it cannot be changed without uninstalling and reinstalling Needle, which will result in data loss.

> **Note:** Needle automatically checks for GPU accessibility and will use the GPU if available to optimize performance.

### What Gets Installed

The installation process sets up:

- **Virtual Environments:** Separate Python environments for backend and image generator services
- **Docker Infrastructure:** PostgreSQL, Milvus, and Redis services via Docker Compose
- **Configuration Files:** Performance-optimized settings based on your chosen mode
- **needlectl CLI:** Command-line interface for managing Needle
- **Web UI:** Optional web interface for easier interaction

After the installation completes, please close and reopen your terminal session (or source your shell configuration file) to ensure that all environment variables are correctly set.

## Starting the Needle Service

Once installed, start the Needle service by running:

```bash
needlectl service start
```

This command will download the required model weights and initiate all the necessary services.

To verify that everything is running as expected, you can check the service status with:

```bash
needlectl service status
```

And confirm the installed version using:
```bash
needlectl --version
```

## About needlectl

The `needlectl` command-line tool is the primary interface for interacting with Needle. It will be discussed in detail in the subsequent sections, where you'll learn how to leverage its full capabilities.
