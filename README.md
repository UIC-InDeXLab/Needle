
# 🪡 Needle: A Database for Image Content Retrieval

Needle is an advanced deployment-ready system for Image retrieval, designed to empower researchers and developers with a powerful tool for querying **images** using natural language descriptions. It’s based on the research presented in [our paper](https://arxiv.org/abs/2412.00639), introducing a novel approach to efficient and scalable retrieval.

🚀 **Why Needle?**
- Seamlessly retrieve image content from large datasets.
- Extendable and modular design to fit various research needs.
- Backed by cutting-edge research for accurate and robust retrieval.
- 200% improvement over CLIP from OpenAI 

---

## 🎥 Demonstration

In this demonstration, we demonstrate Needle's effectiveness on complex natural language queries. In default configuration, Needle generates 4 base images (k = 4) with image size 512x512. 

![Demo](media/demo.gif)

---

## ⚙️ Installation

Installing Needle is quick and straightforward. Make sure you have [Docker](https://www.docker.com/get-started/) and [Docker Compose](https://docs.docker.com/compose/) installed, then, use the one-liner below to install Needle:

```bash  
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/install.sh -o install.sh && bash install.sh && rm install.sh 
```
Then, you can start needle service using this command: 
```bash
needlectl service start
```

### 🧹 Uninstallation

To uninstall Needle, run:

```bash  
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/uninstall.sh | bash  
```  

---

## 🔍 A Little About `needlectl`

`needlectl` is the core command-line utility for interacting with Needle. It allows you to:
- 🔎 Perform searches on multimedia datasets.
- 🛠️ Add or update image datasets (directories) for retrieval.
With `needlectl`, you can easily integrate Needle into your workflows for seamless and intuitive operation.
More on `needlectl` in [here](https://github.com/UIC-InDeXLab/Needle/tree/main/cli)
---

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
