import React, { useState, useEffect } from 'react';
import { Search, Image as ImageIcon, Loader2, AlertCircle } from 'lucide-react';
import { createQuery, search, getSearchLogs, getFile } from '../services/api';

const SearchPage = () => {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [searchLogs, setSearchLogs] = useState([]);
  const [imageUrls, setImageUrls] = useState({});
  const [loadingImages, setLoadingImages] = useState(false);
  const [searchStartTime, setSearchStartTime] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [searchConfig, setSearchConfig] = useState({
    num_images_to_retrieve: 10,
    include_base_images_in_preview: false,
    verbose: false,
    num_images_to_generate: 1,
    generated_image_size: "SMALL",
    num_engines_to_use: 1,
    use_fallback: true
  });

  useEffect(() => {
    loadSearchLogs();
  }, []);

  useEffect(() => {
    // Cleanup image URLs on unmount
    return () => {
      Object.values(imageUrls).forEach(url => {
        if (url.startsWith('blob:')) {
          URL.revokeObjectURL(url);
        }
      });
    };
  }, [imageUrls]);

  // Timer for elapsed time during search
  useEffect(() => {
    let interval;
    if (isSearching && searchStartTime) {
      interval = setInterval(() => {
        setElapsedTime(Date.now() - searchStartTime);
      }, 100);
    } else {
      setElapsedTime(0);
    }
    return () => clearInterval(interval);
  }, [isSearching, searchStartTime]);

  const loadSearchLogs = async () => {
    try {
      const response = await getSearchLogs();
      setSearchLogs(response.data.queries || []);
    } catch (err) {
      console.error('Failed to load search logs:', err);
      // Set empty array if search logs fail to load
      setSearchLogs([]);
    }
  };

  const fetchImage = async (filePath) => {
    try {
      const response = await getFile(filePath);
      const blob = new Blob([response.data], { type: 'image/jpeg' });
      return URL.createObjectURL(blob);
    } catch (err) {
      console.error('Failed to fetch image:', err);
      return null;
    }
  };

  const loadImages = async (imagePaths) => {
    setLoadingImages(true);
    const newImageUrls = {};
    
    for (const path of imagePaths) {
      const url = await fetchImage(path);
      if (url) {
        newImageUrls[path] = url;
      }
    }
    
    setImageUrls(prev => ({ ...prev, ...newImageUrls }));
    setLoadingImages(false);
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setResults([]);
    setSearchStartTime(Date.now());
    
    // Clear previous image URLs
    Object.values(imageUrls).forEach(url => {
      if (url.startsWith('blob:')) {
        URL.revokeObjectURL(url);
      }
    });
    setImageUrls({});

    try {
      // Create query
      const queryResponse = await createQuery(query);
      const queryId = queryResponse.data.qid;

      // Perform search
      const searchResponse = await search(queryId, searchConfig);
      const searchData = searchResponse.data;

      const searchEndTime = Date.now();
      const frontendTiming = searchStartTime ? searchEndTime - searchStartTime : null;
      
      setResults({
        queryId,
        results: searchData.results || [],
        baseImages: searchData.base_images || [],
        previewUrl: searchData.preview_url,
        timings: {
          ...searchData.timings,
          frontend_total_time: frontendTiming ? frontendTiming / 1000 : null
        },
        verboseResults: searchData.verbose_results || {}
      });

      // Load images for display
      if (searchData.results && searchData.results.length > 0) {
        loadImages(searchData.results);
      }

      // Reload search logs
      await loadSearchLogs();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const renderImage = (imageData, index) => {
    if (typeof imageData === 'string') {
      // Base64 image
      return (
        <img
          key={index}
          src={`data:image/jpeg;base64,${imageData}`}
          alt={`Search result ${index + 1}`}
          className="w-full h-48 object-cover rounded-lg"
        />
      );
    } else if (imageData.id) {
      // Image ID - would need to fetch actual image
      return (
        <div
          key={index}
          className="w-full h-48 bg-gray-200 rounded-lg flex items-center justify-center"
        >
          <span className="text-gray-500">Image ID: {imageData.id}</span>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Image Search</h1>
        <p className="mt-2 text-gray-600">
          Search for images using natural language descriptions
        </p>
      </div>

      {/* Search Form */}
      <div className="card">
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
              Search Query
            </label>
            <div className="relative">
              <input
                type="text"
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Describe the image you're looking for..."
                className="input pr-12"
                disabled={isSearching}
              />
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center space-x-2">
                {isSearching && elapsedTime > 0 && (
                  <span className="text-xs text-gray-500">
                    {(elapsedTime / 1000).toFixed(1)}s
                  </span>
                )}
                <button
                  type="submit"
                  disabled={isSearching || !query.trim()}
                  className="p-2 text-needle-600 hover:text-needle-700 disabled:text-gray-400"
                >
                  {isSearching ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Search className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Search Configuration */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Images to Retrieve
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={searchConfig.num_images_to_retrieve}
                onChange={(e) => setSearchConfig(prev => ({
                  ...prev,
                  num_images_to_retrieve: parseInt(e.target.value) || 10
                }))}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Images to Generate
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={searchConfig.num_images_to_generate}
                onChange={(e) => setSearchConfig(prev => ({
                  ...prev,
                  num_images_to_generate: parseInt(e.target.value) || 1
                }))}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Image Size
              </label>
              <select
                value={searchConfig.generated_image_size}
                onChange={(e) => setSearchConfig(prev => ({
                  ...prev,
                  generated_image_size: e.target.value
                }))}
                className="input"
              >
                <option value="SMALL">Small</option>
                <option value="MEDIUM">Medium</option>
                <option value="LARGE">Large</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={searchConfig.use_fallback}
                onChange={(e) => setSearchConfig(prev => ({
                  ...prev,
                  use_fallback: e.target.checked
                }))}
                className="rounded border-gray-300 text-needle-600 focus:ring-needle-500"
              />
              <span className="ml-2 text-sm text-gray-700">Use Fallback</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={searchConfig.include_base_images_in_preview}
                onChange={(e) => setSearchConfig(prev => ({
                  ...prev,
                  include_base_images_in_preview: e.target.checked
                }))}
                className="rounded border-gray-300 text-needle-600 focus:ring-needle-500"
              />
              <span className="ml-2 text-sm text-gray-700">Include Base Images</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={searchConfig.verbose}
                onChange={(e) => setSearchConfig(prev => ({
                  ...prev,
                  verbose: e.target.checked
                }))}
                className="rounded border-gray-300 text-needle-600 focus:ring-needle-500"
              />
              <span className="ml-2 text-sm text-gray-700">Verbose Results</span>
            </label>
          </div>
        </form>
      </div>

      {/* Error Display */}
      {error && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* Search Results */}
      {results.results && results.results.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Search Results</h2>
            {results.timings && (
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">
                  {results.timings.frontend_total_time ? 
                    `${(results.timings.frontend_total_time * 1000).toFixed(0)}ms` : 
                    results.timings.total_request_time ? 
                    `${(results.timings.total_request_time * 1000).toFixed(0)}ms` : 
                    'Timing unavailable'
                  }
                </div>
                <div className="text-xs text-gray-500">
                  {results.timings.frontend_total_time ? 'Total time (frontend)' : 'Backend time'}
                </div>
              </div>
            )}
          </div>

          {/* Detailed Timing Information */}
          {results.timings && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Performance Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                {results.timings.total_request_time && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Request:</span>
                    <span className="font-medium text-gray-900">
                      {(results.timings.total_request_time * 1000).toFixed(0)}ms
                    </span>
                  </div>
                )}
                {results.timings.image_generation && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Image Generation:</span>
                    <span className="font-medium text-gray-900">
                      {(results.timings.image_generation * 1000).toFixed(0)}ms
                    </span>
                  </div>
                )}
                {results.timings.embedding_regnet && results.timings.embedding_regnet.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Embedding (RegNet):</span>
                    <span className="font-medium text-gray-900">
                      {(results.timings.embedding_regnet[0] * 1000).toFixed(0)}ms
                    </span>
                  </div>
                )}
                {results.timings.embedding_eva && results.timings.embedding_eva.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Embedding (EVA):</span>
                    <span className="font-medium text-gray-900">
                      {(results.timings.embedding_eva[0] * 1000).toFixed(0)}ms
                    </span>
                  </div>
                )}
                {results.timings.retrieval_regnet && results.timings.retrieval_regnet.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Retrieval (RegNet):</span>
                    <span className="font-medium text-gray-900">
                      {(results.timings.retrieval_regnet[0] * 1000).toFixed(0)}ms
                    </span>
                  </div>
                )}
                {results.timings.retrieval_eva && results.timings.retrieval_eva.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Retrieval (EVA):</span>
                    <span className="font-medium text-gray-900">
                      {(results.timings.retrieval_eva[0] * 1000).toFixed(0)}ms
                    </span>
                  </div>
                )}
                {results.timings.ranking_aggregation && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Ranking & Aggregation:</span>
                    <span className="font-medium text-gray-900">
                      {(results.timings.ranking_aggregation * 1000).toFixed(2)}ms
                    </span>
                  </div>
                )}
                {results.timings.frontend_total_time && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Frontend Total:</span>
                    <span className="font-medium text-gray-900">
                      {(results.timings.frontend_total_time * 1000).toFixed(0)}ms
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Base Images */}
          {results.baseImages && results.baseImages.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Generated Images</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {results.baseImages.map((image, index) => renderImage(image, index))}
              </div>
            </div>
          )}

          {/* Search Results */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">
              Retrieved Images ({results.results.length})
              {loadingImages && (
                <span className="ml-2 text-sm text-gray-500">
                  <Loader2 className="inline h-4 w-4 animate-spin mr-1" />
                  Loading images...
                </span>
              )}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {results.results.map((result, index) => {
                const imagePath = typeof result === 'string' ? result : result.id || result;
                const imageUrl = imageUrls[imagePath];
                
                return (
                  <div key={index} className="bg-gray-50 rounded-lg p-4">
                    <div className="aspect-square bg-gray-200 rounded-lg flex items-center justify-center mb-2 overflow-hidden">
                      {imageUrl ? (
                        <img
                          src={imageUrl}
                          alt={`Search result ${index + 1}`}
                          className="w-full h-full object-cover rounded-lg"
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                        />
                      ) : null}
                      <div 
                        className={`w-full h-full flex items-center justify-center ${imageUrl ? 'hidden' : 'flex'}`}
                      >
                        <ImageIcon className="h-12 w-12 text-gray-400" />
                      </div>
                    </div>
                    <div className="text-sm text-gray-600 truncate" title={imagePath}>
                      {imagePath.split('/').pop()}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Preview Link */}
          {results.previewUrl && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <a
                href={results.previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
              >
                View Full Gallery
              </a>
            </div>
          )}
        </div>
      )}

      {/* Search Logs */}
      {searchLogs.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Searches</h2>
          <div className="space-y-2">
            {searchLogs.slice(0, 10).map((log, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <span className="text-gray-900">{log.query}</span>
                  {log.timings && log.timings.total_request_time && (
                    <div className="text-xs text-gray-500 mt-1">
                      Completed in {(log.timings.total_request_time * 1000).toFixed(0)}ms
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <span className="text-sm text-gray-500">ID: {log.qid}</span>
                  {log.timestamp && (
                    <div className="text-xs text-gray-400 mt-1">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchPage;
