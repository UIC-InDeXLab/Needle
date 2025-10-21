import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Health Check
export const getHealth = () => api.get('/health');

// Service Status
export const getServiceStatus = () => api.get('/service/status');

// Directory Management
export const getDirectories = () => api.get('/directory');
export const getDirectory = (id) => api.get(`/directory/${id}`);
export const addDirectory = (path) => api.post('/directory', { path });
export const updateDirectory = (id, data) => api.put(`/directory/${id}`, data);
export const removeDirectory = (path) => api.delete('/directory', { data: { path } });

// Query Management
export const createQuery = (query) => api.post('/query', { q: query });
export const getSearchLogs = () => api.get('/search/logs');

// Search
export const search = (queryId, config) => {
  // Get user's generator configuration
  const generatorConfig = getGeneratorConfig();
  const enabledGenerators = generatorConfig.filter(g => g.enabled && g.activated);
  
  // Build engines array from user's configuration
  const engines = enabledGenerators.map(generator => {
    const engine = {
      name: generator.name,
      params: {}
    };
    
    // Add required parameters if they exist
    if (generator.params) {
      Object.keys(generator.params).forEach(key => {
        engine.params[key] = generator.params[key];
      });
    }
    
    // Add default params for specific generators
    if (generator.name === "SDTurbo") {
      engine.params.additionalProp1 = {};
    }
    
    return engine;
  });

  const searchRequest = {
    qid: queryId,
    num_images_to_retrieve: config.num_images_to_retrieve || 10,
    include_base_images_in_preview: config.include_base_images_in_preview || false,
    verbose: config.verbose || false,
    generation_config: {
      engines: engines,
      num_engines_to_use: config.num_engines_to_use || Math.min(engines.length, 1),
      num_images: config.num_images_to_generate || 1,
      image_size: config.generated_image_size || "SMALL",
      use_fallback: config.use_fallback !== false
    }
  };
  return api.post('/search', searchRequest);
};

// Generators
export const getGenerators = () => api.get('/generator');
export const getGeneratorConfig = () => {
  // Get from localStorage or return default
  const config = localStorage.getItem('generatorConfig');
  return config ? JSON.parse(config) : [];
};
export const saveGeneratorConfig = (config) => {
  localStorage.setItem('generatorConfig', JSON.stringify(config));
};
export const updateGeneratorConfig = (generatorName, updates) => {
  const config = getGeneratorConfig();
  const index = config.findIndex(g => g.name === generatorName);
  if (index !== -1) {
    config[index] = { ...config[index], ...updates };
    saveGeneratorConfig(config);
  }
  return config;
};
export const reorderGenerators = (newOrder) => {
  const config = getGeneratorConfig();
  const reorderedConfig = newOrder.map(name => 
    config.find(g => g.name === name)
  ).filter(Boolean);
  saveGeneratorConfig(reorderedConfig);
  return reorderedConfig;
};

// File Access
export const getFile = (filePath) => api.get('/file', {
  params: { file_path: filePath },
  responseType: 'blob'
});

// Gallery
export const getGallery = (queryId) => api.get(`/gallery/${queryId}`);

export default api;
