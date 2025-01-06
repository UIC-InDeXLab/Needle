
# 📌 Needlectl: Needle Command Line Interface  



Needlectl is a command-line tool designed to interact with **Needle**, a system that retrieves and manages visual content. This CLI enables you to efficiently manage directories, perform searches, and control backend services—all through a simple and powerful interface.

---

## 🎯 Goal  

Needlectl provides an intuitive way to manage the Needle system, allowing users to:  
- Add, remove, and list directories containing image datasets.  
- Run advanced search queries on visual data.  
- Start, stop, and restart Needle's backend services with ease.  

It’s a seamless bridge between Needle’s backend and your data management needs.  

---

## 🌟 Key Capabilities  

### 🗂️ Directory Management  
Organize your image datasets by adding or removing directories. Monitor indexing progress and retrieve detailed information about managed directories.  

Commands:  
- **`directory add`**: Add a new directory to Needle.  
- **`directory remove`**: Remove an existing directory.  
- **`directory list`**: List all indexed directories.  
- **`directory describe`**: Get detailed information about a specific directory.  

### 🔍 Search  
Perform advanced searches for visual content using natural language prompts. Customize your search with options like the number of results, clustering size, and output image size.  

Commands:  
- **`search run`**: Execute a search query and retrieve results.  

### ⚙️ Service Control  
Control Needle's backend services, ensuring a smooth and reliable operation.  

Commands:  
- **`service start`**: Start the Needle backend services.  
- **`service stop`**: Stop the Needle backend services.  
- **`service restart`**: Restart Needle’s services.  

---

## 🚀 How It Works  

### CLI Structure  
The CLI has three primary groups of commands:  
1. **Directory Commands**: Manage directories for Needle’s backend.  
2. **Search Commands**: Execute searches for visual content.  
3. **Service Commands**: Control Needle’s backend services.  

### Options  
Global options available across all commands:  
- **`--api-url`**: URL of the Needle backend API (default: `http://127.0.0.1:8000`).  
- **`--output`**: Specify the output format (`human`, `json`, or `yaml`).  

### Output Formats  
Needlectl supports multiple output formats to suit different use cases:  
- **Human-readable** (default): For everyday usage in the terminal.  
- **JSON/YAML**: Structured formats for integration with other tools or scripts.  

---

## 📖 Command Reference  

### 🗂️ Directory Management  

#### **`directory add`**  
Add a directory to Needle.  
```bash
needlectl directory add <path> [--show-progress]
```  
Options:  
- **`<path>`**: Path to the directory to add.  
- **`--show-progress`**: Display real-time indexing progress.  

---

#### **`directory remove`**  
Remove a directory from Needle.  
```bash
needlectl directory remove <path>
```  
Options:  
- **`<path>`**: Path to the directory to remove.  

---

#### **`directory list`**  
List all managed directories.  
```bash
needlectl directory list
```  

---

#### **`directory describe`**  
Get detailed information about a specific directory.  
```bash
needlectl directory describe <directory_id>
```  
Options:  
- **`<directory_id>`**: The ID of the directory to describe.  

---

### 🔍 Search  

#### **`search run`**  
Perform a search using a natural language prompt.  
```bash
needlectl search run <query> [--n <int>] [--k <int>] [--image-size <int>] [--include-base-images]
```  
Options:  
- **`--n`**: Number of results to return (default: `20`).  
- **`--k`**: Number of base (guide) images to generate (default: `4`).  
- **`--image-size`**: Size of the generated base images in pixels (default: `512`).  
- **`--include-base-images`**: Include base images in the results.  

---

### ⚙️ Service Control  

#### **`service start`**  
Start Needle backend services.  
```bash
needlectl service start
```  

---

#### **`service stop`**  
Stop Needle backend services.  
```bash
needlectl service stop
```  

---

#### **`service restart`**  
Restart Needle backend services.  
```bash
needlectl service restart
```  

---

## 💡 Examples  

1. Add a directory and show indexing progress:  
   ```bash
   needlectl directory add /path/to/images --show-progress
   ```  

2. Perform a search query with 10 results and 2 1024x1024 pixel images:  
   ```bash
   needlectl search run "sunset over mountains" --n 10 --image-size 1024 --k 2
   ```  

3. Restart Needle services:  
   ```bash
   needlectl service restart
   ```  

4. List all directories in human-readable format:  
   ```bash
   needlectl directory list --output human
   ```  

---

⚙️ **Empower your workflows with Needlectl!**
