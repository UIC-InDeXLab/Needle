import React, { useState, useEffect } from 'react';
import { 
  FolderOpen, 
  Plus, 
  Trash2, 
  ToggleLeft, 
  ToggleRight, 
  Loader2, 
  AlertCircle,
  RefreshCw
} from 'lucide-react';
// Removed unused API imports - using mockApi instead
import { mockApi } from '../services/mockApi';

const DirectoryPage = () => {
  const [directories, setDirectories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newDirectoryPath, setNewDirectoryPath] = useState('');
  const [addingDirectory, setAddingDirectory] = useState(false);
  const [selectedDirectory, setSelectedDirectory] = useState(null);
  const [directoryDetails, setDirectoryDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadDirectories();
  }, []);

  // Auto-refresh every second when autoRefresh is enabled
  useEffect(() => {
    let interval;
    if (autoRefresh) {
      interval = setInterval(() => {
        loadDirectories(false); // Don't show loading spinner during auto-refresh
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const loadDirectories = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      setError(null);
      const response = await mockApi.getDirectories();
      const directories = response.data || [];
      
      // Debug: Log the indexing progress
      const indexingDir = directories.find(d => d.status === "indexing");
      if (indexingDir) {
        console.log(`Indexing progress: ${Math.round(indexingDir.indexing_ratio * 100)}%`);
      }
      
      setDirectories(directories);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load directories');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const loadDirectoryDetails = async (id) => {
    try {
      setLoadingDetails(true);
      const response = await mockApi.getDirectory(id);
      setDirectoryDetails(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load directory details');
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleAddDirectory = async (e) => {
    e.preventDefault();
    if (!newDirectoryPath.trim()) return;

    try {
      setAddingDirectory(true);
      setError(null);
      await mockApi.addDirectory(newDirectoryPath);
      setNewDirectoryPath('');
      setShowAddForm(false);
      await loadDirectories();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to add directory');
    } finally {
      setAddingDirectory(false);
    }
  };

  const handleToggleDirectory = async (id, isEnabled) => {
    try {
      await mockApi.updateDirectory(id, { is_enabled: !isEnabled });
      await loadDirectories();
      if (selectedDirectory === id) {
        await loadDirectoryDetails(id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to update directory');
    }
  };

  const handleRemoveDirectory = async (path) => {
    if (!window.confirm(`Are you sure you want to remove directory "${path}"?`)) return;

    try {
      await mockApi.removeDirectory(path);
      await loadDirectories();
      if (selectedDirectory && directoryDetails?.path === path) {
        setSelectedDirectory(null);
        setDirectoryDetails(null);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to remove directory');
    }
  };

  const getIndexingStatus = (directory) => {
    if (directory.status === "indexing") return 'Indexing...';
    if (!directory.is_indexed) return 'Not Indexed';
    return 'Indexed';
  };

  const getIndexingColor = (directory) => {
    if (directory.status === "indexing") return 'text-blue-600 bg-blue-100';
    if (!directory.is_indexed) return 'text-red-600 bg-red-100';
    return 'text-green-600 bg-green-100';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Directory Management</h1>
          <p className="mt-2 text-gray-600">
            Manage image directories for indexing and search
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn btn-primary flex items-center"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Directory
        </button>
      </div>

      {/* Add Directory Form */}
      {showAddForm && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Add New Directory</h2>
          <form onSubmit={handleAddDirectory} className="space-y-4">
            <div>
              <label htmlFor="directoryPath" className="block text-sm font-medium text-gray-700 mb-2">
                Directory Path
              </label>
              <input
                type="text"
                id="directoryPath"
                value={newDirectoryPath}
                onChange={(e) => setNewDirectoryPath(e.target.value)}
                placeholder="/path/to/your/images"
                className="input"
                disabled
                title="Disabled in demo"
              />
            </div>
            <div className="flex space-x-3">
              <button
                type="submit"
                disabled
                className="btn btn-primary flex items-center"
                title="Disabled in demo"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Directory
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="btn btn-secondary"
                disabled={addingDirectory}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* Directories List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Directories Table */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Directories</h2>
            <div className="flex items-center space-x-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded border-gray-300 text-needle-600 focus:ring-needle-500"
                />
                <span className="ml-2 text-sm text-gray-700">Auto-refresh</span>
              </label>
              <button
                onClick={() => loadDirectories()}
                disabled={loading}
                className="btn btn-secondary flex items-center"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-needle-600" />
            </div>
          ) : directories.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FolderOpen className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No directories added yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {directories.map((directory) => (
                <div
                  key={directory.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedDirectory === directory.id
                      ? 'border-needle-300 bg-needle-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => {
                    setSelectedDirectory(directory.id);
                    loadDirectoryDetails(directory.id);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {directory.path}
                      </p>
                      <div className="flex items-center mt-1 space-x-2">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getIndexingColor(directory)}`}
                        >
                          {directory.status === "indexing" ? "Indexing..." : getIndexingStatus(directory)}
                        </span>
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            directory.is_enabled
                              ? 'text-green-600 bg-green-100'
                              : 'text-gray-600 bg-gray-100'
                          }`}
                        >
                          {directory.is_enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                      {/* Progress Bar */}
                      {directory.status === "indexing" && directory.indexing_ratio !== undefined && (
                        <div className="mt-2">
                          <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                            <span>Indexing Progress</span>
                            <span>{Math.round(directory.indexing_ratio * 100)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-needle-600 h-2 rounded-full transition-all duration-500"
                              style={{ width: `${directory.indexing_ratio * 100}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center space-x-2 ml-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleDirectory(directory.id, directory.is_enabled);
                        }}
                        className="p-1 text-gray-300 cursor-not-allowed"
                        title="Disabled in demo"
                        disabled
                      >
                        {directory.is_enabled ? (
                          <ToggleRight className="h-5 w-5 text-green-600" />
                        ) : (
                          <ToggleLeft className="h-5 w-5" />
                        )}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveDirectory(directory.path);
                        }}
                        className="p-1 text-gray-300 cursor-not-allowed"
                        title="Disabled in demo"
                        disabled
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Directory Details */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Directory Details</h2>
          {!selectedDirectory ? (
            <div className="text-center py-8 text-gray-500">
              <FolderOpen className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Select a directory to view details</p>
            </div>
          ) : loadingDetails ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-needle-600" />
            </div>
          ) : directoryDetails ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Path</label>
                <p className="mt-1 text-sm text-gray-900 break-all">{directoryDetails.directory.path}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Status</label>
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getIndexingColor(directoryDetails.directory)}`}
                  >
                    {getIndexingStatus(directoryDetails.directory)}
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Enabled</label>
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      directoryDetails.directory.is_enabled
                        ? 'text-green-600 bg-green-100'
                        : 'text-gray-600 bg-gray-100'
                    }`}
                  >
                    {directoryDetails.directory.is_enabled ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>

              {directoryDetails.indexing_ratio !== undefined && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Indexing Progress</label>
                  <div className="mt-1">
                    <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                      <span>Progress</span>
                      <span>{Math.round(directoryDetails.indexing_ratio * 100)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-needle-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${directoryDetails.indexing_ratio * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {directoryDetails.images && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Images</label>
                  <p className="mt-1 text-sm text-gray-900">
                    {directoryDetails.images.length} images found
                  </p>
                  {directoryDetails.images.length > 0 && (
                    <div className="mt-2 max-h-32 overflow-y-auto">
                      <div className="space-y-1">
                        {directoryDetails.images.slice(0, 10).map((image, index) => (
                          <div key={index} className="text-xs text-gray-600 truncate">
                            {image}
                          </div>
                        ))}
                        {directoryDetails.images.length > 10 && (
                          <div className="text-xs text-gray-500">
                            ... and {directoryDetails.images.length - 10} more
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-red-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-4" />
              <p>Failed to load directory details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DirectoryPage;
