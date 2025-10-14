import React, { useState, useEffect, useCallback } from 'react';
import { 
  Settings, 
  RefreshCw, 
  Loader2, 
  AlertCircle, 
  CheckCircle,
  XCircle,
  ChevronUp,
  ChevronDown,
  Save
} from 'lucide-react';
import { 
  getGenerators, 
  getServiceStatus,
  getGeneratorConfig, 
  saveGeneratorConfig, 
  updateGeneratorConfig,
  reorderGenerators 
} from '../services/api';

const GeneratorPage = () => {
  const [generators, setGenerators] = useState([]);
  const [serviceStatus, setServiceStatus] = useState(null);
  const [generatorConfig, setGeneratorConfig] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingGenerator, setEditingGenerator] = useState(null);
  const [configParams, setConfigParams] = useState({});

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (generators.length > 0) {
      loadGeneratorConfig();
    }
  }, [generators]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [generatorsResponse, statusResponse] = await Promise.all([
        getGenerators(),
        getServiceStatus()
      ]);
      
      setGenerators(generatorsResponse.data || []);
      setServiceStatus(statusResponse.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load generator data');
    } finally {
      setLoading(false);
    }
  };

  const loadGeneratorConfig = useCallback(() => {
    const config = getGeneratorConfig();
    if (config.length === 0) {
      // Initialize with default configuration from available generators
      const defaultConfig = generators.map(generator => ({
        ...generator,
        enabled: generator.name === 'SDTurbo', // Enable SDTurbo by default
        activated: generator.name === 'SDTurbo',
        params: {}
      }));
      setGeneratorConfig(defaultConfig);
      saveGeneratorConfig(defaultConfig);
    } else {
      setGeneratorConfig(config);
    }
  }, [generators]);

  const handleToggleActivation = (generatorName) => {
    const updatedConfig = updateGeneratorConfig(generatorName, {
      activated: !generatorConfig.find(g => g.name === generatorName)?.activated
    });
    setGeneratorConfig(updatedConfig);
  };

  const handleToggleEnabled = (generatorName) => {
    const updatedConfig = updateGeneratorConfig(generatorName, {
      enabled: !generatorConfig.find(g => g.name === generatorName)?.enabled
    });
    setGeneratorConfig(updatedConfig);
  };

  const handleEditGenerator = (generator) => {
    setEditingGenerator(generator);
    setConfigParams(generator.params || {});
  };

  const handleSaveGenerator = () => {
    if (editingGenerator) {
      const updatedConfig = updateGeneratorConfig(editingGenerator.name, {
        params: configParams
      });
      setGeneratorConfig(updatedConfig);
      setEditingGenerator(null);
      setConfigParams({});
    }
  };

  const handleMoveUp = (index) => {
    if (index > 0) {
      const newOrder = [...generatorConfig];
      [newOrder[index - 1], newOrder[index]] = [newOrder[index], newOrder[index - 1]];
      const reorderedConfig = reorderGenerators(newOrder.map(g => g.name));
      setGeneratorConfig(reorderedConfig);
    }
  };

  const handleMoveDown = (index) => {
    if (index < generatorConfig.length - 1) {
      const newOrder = [...generatorConfig];
      [newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]];
      const reorderedConfig = reorderGenerators(newOrder.map(g => g.name));
      setGeneratorConfig(reorderedConfig);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-600';
      case 'unhealthy': return 'text-red-600';
      case 'unknown': return 'text-yellow-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'unhealthy': return <XCircle className="h-5 w-5 text-red-600" />;
      case 'unknown': return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      default: return <AlertCircle className="h-5 w-5 text-gray-600" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-needle-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Generator Management</h1>
        <button
          onClick={loadData}
          className="btn btn-secondary"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </button>
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

      {/* Service Status */}
      {serviceStatus && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Service Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center">
              {getStatusIcon(serviceStatus.generator?.status)}
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-900">Generator Service</p>
                <p className={`text-sm ${getStatusColor(serviceStatus.generator?.status)}`}>
                  {serviceStatus.generator?.status || 'Unknown'}
                </p>
              </div>
            </div>
            <div className="flex items-center">
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-900">Host</p>
                <p className="text-sm text-gray-500">localhost:8010</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Generator Configuration */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Generator Configuration</h2>
          <div className="text-sm text-gray-500">
            Drag to reorder • First enabled generator will be used
          </div>
        </div>

        <div className="space-y-4">
          {generatorConfig.map((generator, index) => (
            <div
              key={generator.name}
              className={`border rounded-lg p-4 ${
                generator.enabled && generator.activated 
                  ? 'border-green-200 bg-green-50' 
                  : 'border-gray-200 bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {/* Order Controls */}
                  <div className="flex flex-col space-y-1">
                    <button
                      onClick={() => handleMoveUp(index)}
                      disabled={index === 0}
                      className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronUp className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleMoveDown(index)}
                      disabled={index === generatorConfig.length - 1}
                      className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronDown className="h-4 w-4" />
                    </button>
                  </div>

                  {/* Generator Info */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-medium text-gray-900">{generator.name}</h3>
                      <span className="text-sm text-gray-500">#{index + 1}</span>
                    </div>
                    <p className="text-sm text-gray-600">{generator.description}</p>
                    {generator.required_params && generator.required_params.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-gray-500">
                          Required: {generator.required_params.map(p => p.name).join(', ')}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Controls */}
                <div className="flex items-center space-x-2">
                  {/* Activation Toggle */}
                  <button
                    onClick={() => handleToggleActivation(generator.name)}
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      generator.activated
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {generator.activated ? 'Activated' : 'Inactive'}
                  </button>

                  {/* Enable Toggle */}
                  <button
                    onClick={() => handleToggleEnabled(generator.name)}
                    disabled={!generator.activated}
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      generator.enabled
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-800'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {generator.enabled ? 'Enabled' : 'Disabled'}
                  </button>

                  {/* Configure Button */}
                  {generator.required_params && generator.required_params.length > 0 && (
                    <button
                      onClick={() => handleEditGenerator(generator)}
                      className="btn btn-sm btn-secondary"
                    >
                      <Settings className="h-4 w-4 mr-1" />
                      Configure
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Configuration Modal */}
      {editingGenerator && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Configure {editingGenerator.name}
            </h3>
            
            <div className="space-y-4">
              {editingGenerator.required_params.map((param) => (
                <div key={param.name}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {param.name}
                  </label>
                  <input
                    type={param.name.toLowerCase().includes('key') || param.name.toLowerCase().includes('token') ? 'password' : 'text'}
                    value={configParams[param.name] || ''}
                    onChange={(e) => setConfigParams(prev => ({
                      ...prev,
                      [param.name]: e.target.value
                    }))}
                    placeholder={param.description}
                    className="input w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">{param.description}</p>
                </div>
              ))}
            </div>

            <div className="flex justify-end space-x-2 mt-6">
              <button
                onClick={() => {
                  setEditingGenerator(null);
                  setConfigParams({});
                }}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveGenerator}
                className="btn btn-primary"
              >
                <Save className="h-4 w-4 mr-2" />
                Save Configuration
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Available Generators Info */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Available Generators</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {generators.map((generator) => (
            <div key={generator.name} className="border rounded-lg p-4">
              <h3 className="font-medium text-gray-900">{generator.name}</h3>
              <p className="text-sm text-gray-600 mt-1">{generator.description}</p>
              <div className="mt-2">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  generator.status === 'healthy' 
                    ? 'bg-green-100 text-green-800'
                    : generator.status === 'unhealthy'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {generator.status || 'Unknown'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default GeneratorPage;