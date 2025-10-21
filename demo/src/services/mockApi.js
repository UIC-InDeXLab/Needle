// Mock API service for demo
// This file contains all the mock data and API responses

// Sample queries data - loaded from external JSON file
// To customize: Edit src/sample-queries.json and add your images to public/demo-images/
import sampleQueriesData from '../sample-queries.json';

export const sampleQueries = sampleQueriesData.queries;

// Mock search logs
export const mockSearchLogs = [
  {
    qid: "demo_001",
    query: "a cute cat",
    timestamp: new Date(Date.now() - 300000).toISOString(),
    timings: { total_request_time: 1.2 }
  },
  {
    qid: "demo_002",
    query: "mountain landscape", 
    timestamp: new Date(Date.now() - 600000).toISOString(),
    timings: { total_request_time: 0.8 }
  },
  {
    qid: "demo_003",
    query: "red sports car",
    timestamp: new Date(Date.now() - 900000).toISOString(),
    timings: { total_request_time: 1.5 }
  }
];

// Mock directories data
export const mockDirectories = [
  {
    id: 1,
    path: "/home/mahdi/Datasets/LVIS/1000",
    name: "LVIS Dataset",
    status: "indexed",
    is_indexed: true,
    is_enabled: true,
    file_count: 1000,
    last_indexed: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
    index_size: "15.2MB",
    embedding_dimension: 512
  },
  {
    id: 2,
    path: "/home/mahdi/Datasets/COCO/5000",
    name: "COCO Dataset",
    status: "indexing",
    is_indexed: false,
    is_enabled: false,
    file_count: 5000,
    last_indexed: null,
    index_size: "0MB",
    embedding_dimension: 512,
    indexing_ratio: 0.0 // Will be updated dynamically
  }
];

// Mock generators data - using sample generators from assets
export const mockGenerators = [
  {
    name: "DALL-E",
    description: "OpenAI's DALL-E image generation model",
    type: "external_api",
    status: "active",
    enabled: true,
    activated: true,
    required_params: [
      {
        name: "api_key",
        description: "OpenAI API key"
      }
    ],
    stats: {
      images_generated: 42,
      avg_generation_time: 1.2,
      success_rate: 100,
      default_size: "512x512"
    }
  },
  {
    name: "Replicate",
    description: "Replicate.com hosted models",
    type: "external_api",
    status: "active",
    enabled: true,
    activated: true,
    required_params: [
      {
        name: "api_token",
        description: "Replicate API token"
      },
      {
        name: "model",
        description: "Model identifier on Replicate"
      }
    ],
    stats: {
      images_generated: 28,
      avg_generation_time: 2.1,
      success_rate: 98,
      default_size: "1024x1024"
    }
  },
  {
    name: "RealVisXL",
    description: "adirik/realvisxl-v3.0-turbo on Replicate.com",
    type: "external_api",
    status: "active",
    enabled: true,
    activated: true,
    required_params: [
      {
        name: "api_token",
        description: "Replicate API token"
      }
    ],
    stats: {
      images_generated: 15,
      avg_generation_time: 3.5,
      success_rate: 95,
      default_size: "1024x1024"
    }
  },
  {
    name: "SDTurbo",
    description: "Image generator using SD-Turbo",
    type: "local",
    status: "active",
    enabled: true,
    activated: true,
    required_params: [],
    stats: {
      images_generated: 67,
      avg_generation_time: 0.8,
      success_rate: 99,
      default_size: "512x512"
    }
  }
];

// Mock service status
export const mockServiceStatus = {
  backend: { status: "online", uptime: "7 days", healthy: true },
  database: { status: "connected", uptime: "7 days", healthy: true },
  vector_db: { status: "ready", uptime: "7 days", healthy: true },
  generators: { status: "active", uptime: "7 days", healthy: true }
};

// Mock performance metrics
export const mockPerformanceMetrics = {
  total_searches: 42,
  avg_response_time: 1.2,
  uptime: 99.9,
  memory_usage: "15.2MB"
};

// Mock recent activity
export const mockRecentActivity = [
  {
    type: "search",
    message: "Search completed: \"a cute cat\"",
    timestamp: new Date(Date.now() - 120000).toISOString(),
    status: "success"
  },
  {
    type: "generation",
    message: "Image generated successfully",
    timestamp: new Date(Date.now() - 300000).toISOString(),
    status: "success"
  },
  {
    type: "search",
    message: "Search completed: \"mountain landscape\"",
    timestamp: new Date(Date.now() - 480000).toISOString(),
    status: "success"
  }
];

// Helper function to simulate API delay
const simulateDelay = (min = 100, max = 500) => {
  const delay = Math.random() * (max - min) + min;
  return new Promise(resolve => setTimeout(resolve, delay));
};

// Helper function to update indexing progress
const updateIndexingProgress = () => {
  const indexingDir = mockDirectories.find(d => d.status === "indexing");
  if (indexingDir && indexingDir.indexing_ratio < 1.0) {
    indexingDir.indexing_ratio = Math.min(indexingDir.indexing_ratio + 0.01, 1.0);
    
    // When indexing is complete, update status
    if (indexingDir.indexing_ratio >= 1.0) {
      indexingDir.status = "indexed";
      indexingDir.is_indexed = true;
      indexingDir.last_indexed = new Date().toISOString();
      indexingDir.index_size = "25.4MB";
    }
  }
};

// Start the indexing progress simulation
setInterval(updateIndexingProgress, 1000);

// Mock API functions
export const mockApi = {
  // Health Check
  getHealth: async () => {
    await simulateDelay(50, 100);
    return { data: { status: "healthy" } };
  },

  // Service Status
  getServiceStatus: async () => {
    await simulateDelay(100, 200);
    return { data: mockServiceStatus };
  },

  // Directory Management
  getDirectories: async () => {
    await simulateDelay(100, 200);
    return { data: mockDirectories };
  },

  getDirectory: async (id) => {
    await simulateDelay(50, 100);
    const directory = mockDirectories.find(d => d.id === id);
    return { data: { directory: directory } };
  },

  addDirectory: async (path) => {
    await simulateDelay(200, 500);
    const newDirectory = {
      id: mockDirectories.length + 1,
      path,
      name: path.split('/').pop(),
      status: "indexing",
      file_count: 0,
      last_indexed: null,
      index_size: "0MB",
      embedding_dimension: 512
    };
    mockDirectories.push(newDirectory);
    return { data: newDirectory };
  },

  updateDirectory: async (id, data) => {
    await simulateDelay(100, 300);
    const index = mockDirectories.findIndex(d => d.id === id);
    if (index !== -1) {
      mockDirectories[index] = { ...mockDirectories[index], ...data };
    }
    return { data: mockDirectories[index] };
  },

  removeDirectory: async (path) => {
    await simulateDelay(100, 300);
    const index = mockDirectories.findIndex(d => d.path === path);
    if (index !== -1) {
      mockDirectories.splice(index, 1);
    }
    return { data: { success: true } };
  },

  // Query Management
  createQuery: async (query) => {
    await simulateDelay(50, 100);
    const qid = `demo_${Date.now()}`;
    return { data: { qid } };
  },

  getSearchLogs: async () => {
    await simulateDelay(100, 200);
    return { data: { queries: mockSearchLogs } };
  },

  // Search - returns mock data based on query
  search: async (queryId, config) => {
    await simulateDelay(1000, 2000); // Simulate search delay
    
    // Find matching sample query
    const sampleQuery = sampleQueries.find(q => q.id === queryId) || sampleQueries[0];
    
    const mockResults = {
      results: sampleQuery.results, // Return full result objects with similarity scores
      base_images: [sampleQuery.generatedImage.url],
      preview_url: `https://example.com/gallery/${queryId}`,
      timings: {
        total_request_time: 1.2,
        image_generation: 0.3,
        embedding_regnet: [0.4],
        embedding_eva: [0.2],
        retrieval_regnet: [0.1],
        retrieval_eva: [0.1],
        ranking_aggregation: 0.1,
        frontend_total_time: 1.2
      },
      verbose_results: {
        generated_images: [sampleQuery.generatedImage],
        retrieved_images: sampleQuery.results
      }
    };

    return { data: mockResults };
  },

  // Generators
  getGenerators: async () => {
    await simulateDelay(100, 200);
    return { data: mockGenerators };
  },

  getGeneratorConfig: () => {
    const config = localStorage.getItem('generatorConfig');
    return config ? JSON.parse(config) : mockGenerators;
  },

  saveGeneratorConfig: (config) => {
    localStorage.setItem('generatorConfig', JSON.stringify(config));
    return config;
  },

  updateGeneratorConfig: (generatorName, updates) => {
    const config = mockApi.getGeneratorConfig();
    const index = config.findIndex(g => g.name === generatorName);
    if (index !== -1) {
      config[index] = { ...config[index], ...updates };
      mockApi.saveGeneratorConfig(config);
    }
    return config;
  },

  reorderGenerators: (newOrder) => {
    const config = mockApi.getGeneratorConfig();
    const reorderedConfig = newOrder.map(name => 
      config.find(g => g.name === name)
    ).filter(Boolean);
    mockApi.saveGeneratorConfig(reorderedConfig);
    return reorderedConfig;
  },

  // File Access - return placeholder for demo
  getFile: async (filePath) => {
    await simulateDelay(100, 300);
    // Return a placeholder image
    const canvas = document.createElement('canvas');
    canvas.width = 400;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#f3f4f6';
    ctx.fillRect(0, 0, 400, 400);
    ctx.fillStyle = '#6b7280';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Demo Image', 200, 200);
    
    return new Promise(resolve => {
      canvas.toBlob(blob => {
        resolve({ data: blob });
      }, 'image/jpeg');
    });
  },

  // Gallery
  getGallery: async (queryId) => {
    await simulateDelay(100, 200);
    const sampleQuery = sampleQueries.find(q => q.id === queryId) || sampleQueries[0];
    return { data: sampleQuery };
  }
};

export default mockApi;
