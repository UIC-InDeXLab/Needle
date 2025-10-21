# Demo

Experience Needle's capabilities with our interactive demo! The demo showcases the complete Needle workflow: text-to-image generation and similarity search.

## 🎯 What You'll See

The demo demonstrates Needle's core functionality:

1. **Text Queries**: Click on sample queries to see how Needle works
2. **Image Generation**: AI-generated images based on your text prompts
3. **Similarity Search**: Find similar images from a curated dataset
4. **Real-time Results**: See how Needle processes queries and returns results

## 🚀 Try the Demo

<div style="text-align: center; margin: 2rem 0;">
  <a href="https://uic-indexlab.github.io/Needle/" 
     target="_blank" 
     style="display: inline-block; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 1rem 2rem; 
            border-radius: 8px; 
            text-decoration: none; 
            font-weight: bold; 
            font-size: 1.1rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: transform 0.2s ease;">
    🎨 Try Needle Demo
  </a>
</div>

## 📋 Demo Features

### Search Interface
- **Sample Queries**: Pre-defined queries to test different scenarios
- **Generated Images**: See AI-generated images for each query
- **Similarity Results**: Browse through similar images from the dataset
- **Performance Metrics**: View timing information for each search

### Directory Management
- **Dataset Overview**: See indexed directories and their status
- **Indexing Progress**: Watch real-time indexing progress
- **Directory Details**: View file counts, sizes, and metadata

### Generator Configuration
- **Available Generators**: Browse different image generation engines
- **Configuration Options**: See how generators can be configured
- **Service Status**: Monitor generator service health

### System Status
- **Health Monitoring**: Check overall system status
- **Service Overview**: View all running services
- **Performance Metrics**: See system performance indicators

## 🔧 Technical Details

The demo is built with:
- **Frontend**: React with Tailwind CSS
- **Data**: Pre-processed sample queries and images
- **API**: Mock API simulating the full Needle backend
- **Images**: Curated dataset of 1000+ images with embeddings

## 📁 Demo Structure

```
demo/
├── src/
│   ├── sample-queries.json    # Pre-defined queries and results
│   └── services/
│       └── mockApi.js         # Mock API responses
├── public/
│   └── demo-images/           # Sample images
└── scripts/
    └── build-sample-queries.py # Script to generate demo data
```

## 🎨 Customizing the Demo

You can customize the demo with your own queries and images:

1. **Add Images**: Place your images in `public/demo-images/`
2. **Update Queries**: Edit `src/sample-queries.json`
3. **Rebuild**: Run the build script to update the demo

For detailed customization instructions, see the [Demo Customization Guide](https://github.com/UIC-IndexLab/Needle/tree/main/demo/CUSTOMIZE_DEMO.md).

## 🚀 Getting Started with Needle

After trying the demo, you can:

1. **Install Needle**: Follow our [Getting Started](getting-started.md) guide
2. **Use Needlectl**: Learn about our [command-line interface](needlectl/README.md)
3. **Configure Services**: Set up your own image generation and search pipeline

---

*The demo is updated automatically with each release. For the latest features, make sure you're viewing the most recent version.*
