import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  RefreshCw, 
  Loader2, 
  AlertCircle, 
  CheckCircle,
  Server,
  Database,
  Image as ImageIcon,
  Clock
} from 'lucide-react';
import { 
  getHealth, 
  getServiceStatus, 
  getDirectories, 
  getGenerators,
  getSearchLogs 
} from '../services/api';

const StatusPage = () => {
  const [status, setStatus] = useState({
    health: null,
    service: null,
    directories: null,
    generators: null,
    searchLogs: null
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    loadAllStatus();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadAllStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadAllStatus = async () => {
    try {
      setLoading(true);
      setError(null);

      const [
        healthResponse,
        serviceResponse,
        directoriesResponse,
        generatorsResponse,
        searchLogsResponse
      ] = await Promise.allSettled([
        getHealth(),
        getServiceStatus(),
        getDirectories(),
        getGenerators(),
        getSearchLogs().catch(() => ({ data: { queries: [] } })) // Handle search logs error gracefully
      ]);

      setStatus({
        health: healthResponse.status === 'fulfilled' ? healthResponse.value.data : null,
        service: serviceResponse.status === 'fulfilled' ? serviceResponse.value.data : null,
        directories: directoriesResponse.status === 'fulfilled' ? directoriesResponse.value.data : null,
        generators: generatorsResponse.status === 'fulfilled' ? generatorsResponse.value.data : null,
        searchLogs: searchLogsResponse.status === 'fulfilled' ? searchLogsResponse.value.data : null
      });

      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message || 'Failed to load status information');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (isHealthy) => {
    return isHealthy ? (
      <CheckCircle className="h-5 w-5 text-green-600" />
    ) : (
      <AlertCircle className="h-5 w-5 text-red-600" />
    );
  };

  const getStatusText = (isHealthy) => {
    return isHealthy ? 'Healthy' : 'Unhealthy';
  };

  const getStatusColor = (isHealthy) => {
    return isHealthy ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100';
  };

  // const formatTimestamp = (timestamp) => {
  //   if (!timestamp) return 'Never';
  //   return new Date(timestamp).toLocaleString();
  // };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Status</h1>
          <p className="mt-2 text-gray-600">
            Monitor the health and performance of the Needle system
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {lastUpdated && (
            <div className="text-sm text-gray-500 flex items-center">
              <Clock className="h-4 w-4 mr-1" />
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          )}
          <button
            onClick={loadAllStatus}
            disabled={loading}
            className="btn btn-secondary flex items-center"
          >
            <RefreshCw className={`h-5 w-5 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
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

      {/* Main Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* API Health */}
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-needle-100 rounded-lg">
              <Server className="h-6 w-6 text-needle-600" />
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-900">API Health</p>
              <div className="flex items-center mt-1">
                {getStatusIcon(!!status.health)}
                <span className={`ml-2 text-sm ${getStatusColor(!!status.health)}`}>
                  {getStatusText(!!status.health)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Service Status */}
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Activity className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-900">Service</p>
              <div className="flex items-center mt-1">
                {getStatusIcon(!!status.service)}
                <span className={`ml-2 text-sm ${getStatusColor(!!status.service)}`}>
                  {status.service?.status || 'Unknown'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Directories */}
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <Database className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-900">Directories</p>
              <div className="flex items-center mt-1">
                {getStatusIcon(!!status.directories)}
                <span className="ml-2 text-sm text-gray-600">
                  {status.directories?.directories?.length || 0} configured
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Generators */}
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <ImageIcon className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-900">Generators</p>
              <div className="flex items-center mt-1">
                {getStatusIcon(!!status.generators)}
                <span className="ml-2 text-sm text-gray-600">
                  {status.generators?.length || 0} available
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Status Information */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Directories Status */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Directory Status</h2>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-needle-600" />
            </div>
          ) : status.directories?.directories ? (
            <div className="space-y-3">
              {status.directories.directories.map((directory) => (
                <div key={directory.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {directory.path}
                    </p>
                    <div className="flex items-center mt-1 space-x-2">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          directory.is_indexed
                            ? 'text-green-600 bg-green-100'
                            : 'text-yellow-600 bg-yellow-100'
                        }`}
                      >
                        {directory.is_indexed ? 'Indexed' : 'Not Indexed'}
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
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Database className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No directory information available</p>
            </div>
          )}
        </div>

        {/* Generators Status */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Generator Status</h2>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-needle-600" />
            </div>
          ) : status.generators ? (
            <div className="space-y-3">
              {status.generators.map((generator, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{generator.name}</p>
                    <p className="text-xs text-gray-600 mt-1">{generator.description}</p>
                  </div>
                  <div className="flex items-center">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="ml-2 text-xs text-green-600">Available</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <ImageIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No generator information available</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      {status.searchLogs?.queries && status.searchLogs.queries.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
          <div className="space-y-3">
            {status.searchLogs.queries.slice(0, 5).map((query, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{query.query}</p>
                  <p className="text-xs text-gray-600">Query ID: {query.qid}</p>
                </div>
                <div className="text-xs text-gray-500">
                  Recent
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Information */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">System Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">API Endpoint</label>
            <p className="mt-1 text-sm text-gray-900">http://localhost:8000</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Generator Service</label>
            <p className="mt-1 text-sm text-gray-900">localhost:8010</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Database</label>
            <p className="mt-1 text-sm text-gray-900">PostgreSQL (localhost:5432)</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Vector Database</label>
            <p className="mt-1 text-sm text-gray-900">Milvus (localhost:19530)</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatusPage;
