import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

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

// Setup / onboarding
export const getSetupStatus = () => api.get('/setup/status');
export const getSetupOptions = () => api.get('/setup/options');
export const configureSetup = (profile, useGpu) =>
  api.post('/setup/configure', { profile, use_gpu: useGpu });
export const setSetupGpu = (useGpu) => api.post('/setup/gpu', { use_gpu: useGpu });

// On-device image generation
export const getGenerateModels = () => api.get('/generate/models');
export const getGenerateState = () => api.get('/generate/state');
export const loadGenerateModel = (model) => api.post('/generate/load', { model });
// Generation can take a while on the first call (model load + warmup).
export const generateImages = (payload) =>
  api.post('/generate/images', payload, { timeout: 600000 });
export const saveGeneratedImage = (image, directory, filename) =>
  api.post('/generate/save', { image, directory, filename });


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
  // Ordered, enabled generators define the fallback chain (first = highest
  // priority). When fallback is off, only the first enabled generator is used.
  const fallbackOn = getGeneratorFallback();
  const ordered = getGeneratorConfig().filter((g) => g.enabled);
  const active = fallbackOn ? ordered : ordered.slice(0, 1);

  const engines = active.map((generator) => ({
    name: generator.name,
    params: { ...(generator.params || {}) },
  }));

  const searchRequest = {
    qid: queryId,
    num_images_to_retrieve: config.num_images_to_retrieve || 10,
    include_base_images_in_preview: config.include_base_images_in_preview || false,
    verbose: config.verbose || false,
    generation_config: {
      engines: engines,
      num_engines_to_use: 1,
      num_images: config.num_images_to_generate || 1,
      image_size: config.generated_image_size || "SMALL",
      use_fallback: fallbackOn,
    },
  };
  return api.post('/search', searchRequest);
};

// Generators
export const getGenerators = () => api.get('/generator');
// Discover the models/limits a connected Needle Generator service advertises.
// Returns {} when the service is unreachable. base_url is optional (falls back
// to saved credentials on the backend).
export const getGeneratorCapabilities = (name, baseUrl) =>
  api.get(`/generator/${name}/capabilities`, { params: baseUrl ? { base_url: baseUrl } : {} });
// Persist API credentials for an engine (e.g. { api_key: '...' }) on the backend.
export const setGeneratorCredentials = (name, params) =>
  api.post(`/generator/${name}/credentials`, { params });
// Generate a single test image with an engine (also warms the model). Longer
// timeout since generation can take a while, especially on first (cold) run.
export const testGenerator = (name, params, prompt) =>
  api.post(`/generator/${name}/test`, { params: { ...params, ...(prompt ? { prompt } : {}) } }, { timeout: 180000 });
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
// Global fallback flag: when on, failed generators fall through to the next one
// in the ordered list; when off, only the first enabled generator is used.
export const getGeneratorFallback = () => {
  const v = localStorage.getItem('generatorFallback');
  return v === null ? true : v === 'true';
};
export const setGeneratorFallback = (on) => {
  localStorage.setItem('generatorFallback', on ? 'true' : 'false');
  return on;
};

// File Access
export const getFile = (filePath) => api.get('/file', {
  params: { file_path: filePath },
  responseType: 'blob'
});

// Gallery
export const getGallery = (queryId) => api.get(`/gallery/${queryId}`);

export default api;
