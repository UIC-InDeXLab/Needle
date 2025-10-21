import React, { useState, useEffect } from 'react';
import { Image as ImageIcon, AlertCircle, Play, ExternalLink, Github } from 'lucide-react';
// Removed unused imports: Loader2, getFile
import { sampleQueries, mockApi } from '../services/mockApi';

const SearchPage = () => {
  console.log('SearchPage component loading...');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [searchLogs, setSearchLogs] = useState([]);
  const [imageUrls, setImageUrls] = useState({});
  // Removed loadingImages - not needed for demo
  // Removed searchStartTime - not needed for demo
  const [searchConfig] = useState({
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

  // Removed elapsed time timer - not needed for demo

  const loadSearchLogs = async () => {
    try {
      const response = await mockApi.getSearchLogs();
      setSearchLogs(response.data.queries || []);
    } catch (err) {
      console.error('Failed to load search logs:', err);
      // Set empty array if search logs fail to load
      setSearchLogs([]);
    }
  };

  // Removed fetchImage function - not needed for demo

  // Removed loadImages function - not needed for demo

  const handleSampleQuery = async (sampleQuery) => {
    setIsSearching(true);
    setError(null);
    setResults([]);
    
    // Clear previous image URLs
    Object.values(imageUrls).forEach(url => {
      if (url.startsWith('blob:')) {
        URL.revokeObjectURL(url);
      }
    });
    setImageUrls({});

    try {
      // Record start time right before the actual query request
      const searchStartTime = Date.now();
      
      // Use mock API for demo
      const searchResponse = await mockApi.search(sampleQuery.id, searchConfig);
      const searchData = searchResponse.data;

      const searchEndTime = Date.now();
      const frontendTiming = searchEndTime - searchStartTime;
      
      setResults({
        queryId: sampleQuery.id,
        results: searchData.results || [],
        baseImages: searchData.base_images || [],
        previewUrl: searchData.preview_url,
        timings: {
          ...searchData.timings,
          frontend_total_time: frontendTiming / 1000
        },
        verboseResults: searchData.verbose_results || {}
      });

      // No need to load images - they're already URLs from public directory

      // Reload search logs
      await loadSearchLogs();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  // Removed unused functions: handleSearch and renderImage

  return (
    <div className="space-y-6">
      {/* Demo Information Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-blue-800">
              This is a demo of the Needle image search system
            </h3>
            <div className="mt-2 text-sm text-blue-700">
              <p className="mb-3">
                This demo shows sample queries with pre-generated results. To install and run the actual system with your own images:
              </p>
              <div className="flex flex-col sm:flex-row gap-3">
                <a
                  href="https://github.com/UIC-IndexLab/Needle"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                >
                  <Github className="h-4 w-4 mr-2" />
                  Star us on GitHub
                </a>
                <a
                  href="https://github.com/UIC-IndexLab/Needle#installation"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Installation Guide
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Image Search</h1>
        <p className="mt-2 text-gray-600">
          Search for images using natural language descriptions
        </p>
      </div>

      {/* Sample Queries */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Try These Sample Queries</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sampleQueries.map((sampleQuery) => (
            <button
              key={sampleQuery.id}
              onClick={() => handleSampleQuery(sampleQuery)}
              disabled={isSearching}
              className="p-4 border border-gray-200 rounded-lg hover:border-needle-300 hover:bg-needle-50 transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
                    <Play className="h-6 w-6 text-needle-600" />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {sampleQuery.text}
                  </p>
                  <p className="text-xs text-gray-500">
                    {sampleQuery.results.length} similar images
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
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
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Search Results</h2>
          </div>


          {/* Generated Images */}
          {results.baseImages && results.baseImages.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Generated Images</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {results.baseImages.map((imageUrl, index) => (
                  <div key={index} className="bg-gray-50 rounded-lg p-4">
                    <div className="aspect-square bg-gray-200 rounded-lg flex items-center justify-center mb-2 overflow-hidden">
                      <img
                        src={imageUrl}
                        alt={`Generated ${index + 1}`}
                        className="w-full h-full object-cover rounded-lg"
                        onError={(e) => {
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                      <div className="w-full h-full flex items-center justify-center hidden">
                        <ImageIcon className="h-12 w-12 text-gray-400" />
                      </div>
                    </div>
                    <div className="text-sm text-gray-600 text-center">
                      Generated Image
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Search Results */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">
              Retrieved Images ({results.results.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {results.results.map((result, index) => {
                // Handle both string URLs and object results
                const imageUrl = typeof result === 'string' ? result : result.url;
                
                return (
                  <div key={index} className="bg-gray-50 rounded-lg p-4">
                    <div className="aspect-square bg-gray-200 rounded-lg flex items-center justify-center mb-2 overflow-hidden">
                      <img
                        src={imageUrl}
                        alt={`Result ${index + 1}`}
                        className="w-full h-full object-cover rounded-lg"
                        onError={(e) => {
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                      <div className="w-full h-full flex items-center justify-center hidden">
                        <ImageIcon className="h-12 w-12 text-gray-400" />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

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
