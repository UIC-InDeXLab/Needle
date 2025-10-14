# 🪡 Needle: Unified Installation Guide

This guide covers the new unified installation system for Needle, which uses virtual environments for the backend and image generation hub, while keeping infrastructure services in Docker containers.

## 🏗️ Architecture

- **Backend**: Python virtual environment with direct GPU access
- **Image Generator Hub**: Python virtual environment  
- **Infrastructure Services**: Docker containers
  - PostgreSQL (port 5432)
  - Milvus (port 19530)
  - MinIO (ports 9000-9001)
  - etcd (port 2379)

## 🚀 Quick Start

### Prerequisites

- Python 3.12+ (recommended)
- Docker and Docker Compose
- Git
- NVIDIA GPU with CUDA support (optional, for GPU acceleration)
- macOS with Metal Performance Shaders support (optional, for GPU acceleration)

### Installation

#### Option 1: One-Liner Installation (Recommended)

Install Needle with a single command - no cloning required:

```bash
# Interactive configuration selection
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash

# Or with specific configuration
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s -- fast
```

#### Option 2: Manual Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/UIC-InDeXLab/Needle.git
   cd Needle
   ```

2. **Run the unified installer**:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Start all services**:
   ```bash
   ./start-needle.sh
   ```

4. **Check service status**:
   ```bash
   ./status-needle.sh
   ```

### Configuration Options

Choose your performance configuration:

- **Fast** (Default): Single CLIP model, fastest indexing and retrieval
- **Balanced**: 4 models with balanced performance and accuracy  
- **Accurate**: 6 models with highest accuracy but slower performance

```bash
# Install with specific configuration
./install.sh fast          # Fast mode
./install.sh balanced      # Balanced mode  
./install.sh accurate      # Accurate mode

# Or using Make
make install-fast
make install-balanced
make install-accurate
```

### Using needlectl (Recommended)

After installation, you can use the `needlectl` command to manage services:

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

### Using Make Commands

```bash
# Install Needle (interactive)
make install

# Install with specific configuration
make install-fast
make install-balanced
make install-accurate

# Start all services
make start

# Stop all services
make stop

# Check status
make status

# Development mode (infrastructure + backend with reload)
make dev

# Uninstall
make uninstall
```

## 📋 What the Installer Does

The unified installer (`install.sh`) automatically:

1. **Checks dependencies** (Python, Docker, Git)
2. **Detects GPU availability** (NVIDIA CUDA or macOS MPS)
3. **Clones ImageGeneratorsHub** repository
4. **Creates virtual environments**:
   - `backend/venv` for the Needle backend
   - `../ImageGeneratorsHub/.venv` for the image generator
5. **Installs dependencies** in both virtual environments
6. **Creates configuration files** (`.env`)
7. **Generates management scripts**:
   - `start-needle.sh` - Start all services
   - `stop-needle.sh` - Stop all services
   - `status-needle.sh` - Check service status

## 🔧 Manual Setup

If you prefer to set up manually:

### 1. Backend Setup

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Image Generator Hub Setup

```bash
cd ../ImageGeneratorsHub
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Infrastructure Services

```bash
cd ../Needle
docker compose -f docker/docker-compose.infrastructure.yaml up -d
```

### 4. Start Services

```bash
# Start image generator hub
cd ../ImageGeneratorsHub
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8010 &

# Start backend
cd ../Needle/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
```

## 🌐 Access Points

- **Backend API**: http://localhost:8000
- **Image Generator**: http://localhost:8010
- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Milvus**: localhost:19530

## 📊 Monitoring

- **Backend logs**: `tail -f logs/backend.log`
- **Image generator logs**: `tail -f logs/image-generator-hub.log`
- **Docker services**: `docker ps`
- **Service status**: `./status-needle.sh`

## ⚙️ Configuration

Environment variables are configured in `.env`. Key settings:

- `SERVICE__USE_CUDA=true/false`: Enable GPU acceleration
- `POSTGRES__HOST=localhost`: Database connection
- `MILVUS__HOST=localhost`: Vector database connection
- `GENERATOR__HOST=localhost`: Image generator connection

## 🗑️ Uninstallation

To completely remove Needle:

```bash
./uninstall.sh
```

This will:
- Stop all services
- Remove virtual environments
- Remove configuration files
- Optionally remove Docker volumes (indexed data)
- Optionally remove ImageGeneratorsHub directory

## 🔍 Troubleshooting

### Common Issues

1. **CUDA not available**:
   - Ensure NVIDIA drivers and CUDA are installed
   - Check with `nvidia-smi`
   - On macOS, ensure MPS support is available

2. **Port conflicts**:
   - Check if ports 8000, 8010, 5432, 19530 are available
   - Use `lsof -i :PORT` to check port usage

3. **Docker issues**:
   - Ensure Docker is running: `docker info`
   - Check Docker resources: `docker system df`

4. **Permission issues**:
   - Ensure scripts are executable: `chmod +x *.sh`
   - Check file ownership

5. **Virtual environment issues**:
   - Recreate virtual environments: `rm -rf backend/venv ../ImageGeneratorsHub/.venv`
   - Re-run installer: `./install.sh`

### Logs

Check logs for detailed error information:

```bash
# Backend logs
tail -f logs/backend.log

# Image generator logs  
tail -f logs/image-generator-hub.log

# Docker logs
docker logs postgres
docker logs milvus-standalone
```

## 🆚 Migration from Old Setup

If you have an existing Needle installation:

1. **Stop old services**:
   ```bash
   # If using old venv scripts
   ./stop-needle-venv.sh
   
   # If using Docker
   docker compose down
   ```

2. **Run new installer**:
   ```bash
   ./install.sh
   ```

3. **Start new services**:
   ```bash
   ./start-needle.sh
   ```

The new installer will detect existing virtual environments and update them as needed.

## 🎯 Benefits of Unified Setup

- **Simplified Installation**: Single script handles everything
- **Cross-Platform**: Works on Linux and macOS
- **GPU Support**: Automatic detection and configuration
- **Better Performance**: Direct GPU access without Docker limitations
- **Easier Development**: Native Python execution with hot reload
- **Unified Management**: Single set of start/stop/status scripts

## 📚 Additional Resources

- [Main README](README.md) - Project overview and features
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [Research Paper](https://arxiv.org/abs/2412.00639) - Academic background
