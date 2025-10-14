# 🪡 Needle Installation Options

This document outlines the different ways to install and configure Needle.

## 🚀 Installation Methods

### 1. One-Liner Installation (Recommended)

Install Needle with a single command - no cloning required:

```bash
# Interactive configuration selection
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash

# Or with specific configuration
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/install-oneliner.sh | bash -s -- fast
```

**What it does:**
- Downloads and clones the repository to `~/needle`
- Sets up virtual environments for backend and image generator
- Configures Docker infrastructure services
- Creates management scripts
- Installs with your chosen configuration

### 2. Manual Installation

```bash
# Clone the repository
git clone https://github.com/UIC-InDeXLab/Needle.git
cd Needle

# Run the unified installer
chmod +x install.sh
./install.sh

# Start all services
./start-needle.sh
```

### 3. Make Commands

```bash
# Interactive installation
make install

# Specific configurations
make install-fast
make install-balanced
make install-accurate

# Service management
make start
make stop
make status
make dev
```

## ⚙️ Configuration Options

### Fast Mode (Default)
- **Models**: Single CLIP model
- **Performance**: Fastest indexing and retrieval
- **Use Case**: Quick setup, development, testing
- **Resource Usage**: Low memory and GPU usage

### Balanced Mode
- **Models**: 4 models (DINO, ConvNeXtV2, CLIP, EVA)
- **Performance**: Balanced speed and accuracy
- **Use Case**: Production with good performance
- **Resource Usage**: Moderate memory and GPU usage

### Accurate Mode
- **Models**: 6 models (EVA, RegNet, DINO, CLIP, ConvNeXtV2, BeiT)
- **Performance**: Highest accuracy but slower
- **Use Case**: Research, maximum accuracy needed
- **Resource Usage**: High memory and GPU usage

## 🔧 Configuration Details

### Fast Mode Configuration
```json
{
  "image_embedders": [
    {
      "name": "clip",
      "model_name": "vit_large_patch14_clip_336.openai_ft_in12k_in1k",
      "weight": 1
    }
  ]
}
```

### Balanced Mode Configuration
```json
{
  "image_embedders": [
    {
      "name": "dino",
      "model_name": "vit_large_patch14_reg4_dinov2.lvd142m",
      "weight": 0.25
    },
    {
      "name": "convnextv2",
      "model_name": "convnextv2_large.fcmae_ft_in22k_in1k_384",
      "weight": 0.25
    },
    {
      "name": "clip",
      "model_name": "vit_base_patch16_clip_224.openai",
      "weight": 0.25
    },
    {
      "name": "eva",
      "model_name": "eva02_large_patch14_448.mim_m38m_ft_in22k_in1k",
      "weight": 0.25
    }
  ]
}
```

### Accurate Mode Configuration
```json
{
  "image_embedders": [
    {
      "name": "eva",
      "model_name": "eva02_large_patch14_448.mim_m38m_ft_in22k_in1k",
      "weight": 0.8497
    },
    {
      "name": "regnet",
      "model_name": "regnety_1280.swag_ft_in1k",
      "weight": 0.8235
    },
    {
      "name": "dino",
      "model_name": "vit_large_patch14_reg4_dinov2.lvd142m",
      "weight": 0.8235
    },
    {
      "name": "clip",
      "model_name": "vit_large_patch14_clip_336.openai_ft_in12k_in1k",
      "weight": 0.8146
    },
    {
      "name": "convnextv2",
      "model_name": "convnextv2_large.fcmae_ft_in22k_in1k_384",
      "weight": 0.8184
    },
    {
      "name": "bevit",
      "model_name": "beitv2_large_patch16_224.in1k_ft_in22k_in1k",
      "weight": 0.7660
    }
  ]
}
```

## 🎯 Choosing the Right Configuration

### Choose Fast Mode If:
- You're setting up for development or testing
- You have limited GPU memory (< 8GB)
- You need the fastest possible indexing
- You're okay with slightly lower accuracy

### Choose Balanced Mode If:
- You want a good balance of speed and accuracy
- You have moderate GPU memory (8-16GB)
- You're setting up for production use
- You want reliable performance

### Choose Accurate Mode If:
- You need the highest possible accuracy
- You have plenty of GPU memory (> 16GB)
- You're doing research or academic work
- Speed is less important than accuracy

## 🔄 Changing Configuration

To change your configuration after installation:

1. **Stop services**:
   ```bash
   ./stop-needle.sh
   ```

2. **Reinstall with new configuration**:
   ```bash
   ./install.sh balanced  # or fast/accurate
   ```

3. **Start services**:
   ```bash
   ./start-needle.sh
   ```

## 📊 Performance Comparison

| Mode | Models | Indexing Speed | Query Speed | Accuracy | Memory Usage |
|------|--------|----------------|-------------|----------|--------------|
| Fast | 1 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Balanced | 4 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Accurate | 6 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

## 🛠️ Troubleshooting

### Configuration Issues
- If you get model loading errors, try a lower configuration mode
- If you have GPU memory issues, use Fast mode
- If accuracy is too low, try Balanced or Accurate mode

### Installation Issues
- Make sure you have Python 3.12+ installed
- Ensure Docker is running
- Check that you have sufficient disk space (at least 10GB)
- Verify GPU drivers are installed for GPU acceleration

### Service Issues
- Check logs: `tail -f logs/backend.log`
- Verify configuration: `cat .env`
- Check service status: `./status-needle.sh`
