# 🪡 Needle: A Database for Image Content Retrieval

<p align="center">
  <img src="docs/src/media/needle-banner-transparent.png" width="300" style="border-radius: 20px;" alt="Needle Banner"/>
</p>

<p align="center">
  <a href="https://uic-indexlab.github.io/Needle/overview.html">
    <img src="https://img.shields.io/badge/doc-Homepage-blue" alt="Homepage">
  </a>
  <a href="https://arxiv.org/abs/2412.00639">
    <img src="https://img.shields.io/badge/arXiv-Link-orange" alt="ArXiv">
  </a>
  <a href="https://www.youtube.com/watch?v=n-SXX_ry9-0&t=122s">
    <img src="https://img.shields.io/badge/demo-Youtube-purple" alt="Youtube">
  </a>
</p>


Needle is a deployment-ready system for Image retrieval, designed to empower researchers and developers with a powerful tool for querying **images** using natural language descriptions. It’s based on the research presented in [our paper](https://arxiv.org/abs/2412.00639), introducing a novel approach to efficient and scalable retrieval.

🚀 **Why Needle?**
- Seamlessly retrieve image content from large datasets.
- Extendable and modular design to fit various research needs.
- Backed by cutting-edge research for accurate and robust retrieval.
- 200% improvement over CLIP from OpenAI 

---

## 🎥 Demonstration

Watch as Needle transforms natural language queries into precise image retrieval results in real time.

<p align="center">
    <img src="media/needle_demo.gif"/>
</p>

---

## ⚙️ Installation

Installing Needle is quick and straightforward. Make sure you have [Docker](https://www.docker.com/get-started/) and [Docker Compose](https://docs.docker.com/compose/) installed, then, use the one-liner below to install Needle:

```bash  
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/install.sh -o install.sh && bash install.sh && rm install.sh 
```
For MacOS
```bash
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/refs/heads/linh/install_macos.sh -o install_macos.sh && bash install_macos.sh && rm install_macos.sh
```
Then, you can start needle service using this command: 
```bash
needlectl service start
```

## 🏭 Production

To launch the CPU-based stack with your production configs (located in `$NEEDLE_HOME/configs/`),
use the production override:
```bash
docker compose -f docker/docker-compose.cpu.yaml -f docker/docker-compose.prod.yaml up -d
```

## 🛠️ Development
You can start the full CPU-based stack (etcd, MinIO, Milvus, Postgres, image-generator-hub)
and launch the backend in hot‑reload dev mode with one command:

```bash
make dev
```

This runs core services in detached mode, then rebuilds and starts the backend
with your local code mounted and Uvicorn reload enabled.

For GPU development use:

```bash
make dev-gpu
```

### 📄 Documentation 

Checkout [Needle documentation](https://www.cs.uic.edu/~indexlab/Needle/) to learn more about Needle CLI and its capabilities.


## 📚 Reference

Needle is developed as part of the research presented in our paper:
- [**Needle: A Generative-AI Powered Monte Carlo Method for Answering Complex Natural Language Queries on Multi-modal Data**](https://arxiv.org/abs/2412.00639)

If you use Needle in your work, please cite our paper to support the project:

```bibtex  
@article{erfanian2024needle,
  title={Needle: A Generative-AI Powered Monte Carlo Method for Answering Complex Natural Language Queries on Multi-modal Data},
  author={Erfanian, Mahdi and Dehghankar, Mohsen and Asudeh, Abolfazl},
  journal={arXiv preprint arXiv:2412.00639},
  year={2024}
}
```  

---  

## 🌟 Contributions & Feedback

We welcome contributions, feedback, and discussions! Feel free to open issues or submit pull requests in our [GitHub repository](https://github.com/UIC-InDeXLab/Needle).

Let’s build the future of multimodal content retrieval together!

---
