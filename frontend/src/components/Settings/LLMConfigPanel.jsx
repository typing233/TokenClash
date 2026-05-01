import { useState, useEffect } from 'react';
import { Settings, Key, Globe, Cpu, RefreshCw, CheckCircle, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react';
import { modelsApi } from '../../services/api';

export default function LLMConfigPanel() {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState({});
  const [showApiKey, setShowApiKey] = useState({});
  const [testResults, setTestResults] = useState({});
  
  const [editingConfig, setEditingConfig] = useState(null);
  const [newConfig, setNewConfig] = useState({
    name: '',
    base_url: '',
    api_key: '',
    model_name: '',
    display_name: ''
  });
  const [showNewForm, setShowNewForm] = useState(false);

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      setLoading(true);
      const response = await modelsApi.getAll();
      const models = response.data.models || [];
      const storedConfigs = JSON.parse(localStorage.getItem('llmConfigs') || '[]');
      
      const mergedConfigs = storedConfigs.length > 0 ? storedConfigs : models.map((m, i) => ({
        id: m.model_id,
        name: m.display_name,
        base_url: localStorage.getItem(`llm_${i}_base_url`) || 'https://ark.cn-beijing.volces.com/api/v3',
        api_key: localStorage.getItem(`llm_${i}_api_key`) || '',
        model_name: m.model_name,
        display_name: m.display_name,
        is_default: i === 0
      }));
      
      setConfigs(mergedConfigs);
    } catch (error) {
      console.error('Failed to load configs:', error);
      const storedConfigs = JSON.parse(localStorage.getItem('llmConfigs') || '[]');
      setConfigs(storedConfigs);
    } finally {
      setLoading(false);
    }
  };

  const saveConfigs = (updatedConfigs) => {
    localStorage.setItem('llmConfigs', JSON.stringify(updatedConfigs));
    setConfigs(updatedConfigs);
  };

  const updateConfigField = (index, field, value) => {
    const updated = [...configs];
    updated[index] = { ...updated[index], [field]: value };
    saveConfigs(updated);
  };

  const testConnection = async (index) => {
    const config = configs[index];
    if (!config.base_url || !config.api_key) {
      setTestResults(prev => ({
        ...prev,
        [index]: { success: false, message: '请填写完整的API配置' }
      }));
      return;
    }

    setTesting(prev => ({ ...prev, [index]: true }));
    setTestResults(prev => ({ ...prev, [index]: null }));

    try {
      const response = await testLLMConnection(config);
      
      setTestResults(prev => ({
        ...prev,
        [index]: { success: true, message: '连接成功！', models: response }
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [index]: { 
          success: false, 
          message: error.message || '连接失败，请检查配置' 
        }
      }));
    } finally {
      setTesting(prev => ({ ...prev, [index]: false }));
    }
  };

  const testLLMConnection = async (config) => {
    const baseUrl = config.base_url.replace(/\/$/, '');
    
    try {
      const response = await fetch(`${baseUrl}/models`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${config.api_key}`
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('API密钥无效，请检查您的API密钥');
        }
        throw new Error(`API返回错误: ${response.status}`);
      }

      const data = await response.json();
      return data.data || data.models || [];
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('网络错误，请检查网络连接和API地址');
      }
      throw error;
    }
  };

  const addNewConfig = () => {
    const newConfigEntry = {
      id: `model_${Date.now()}`,
      name: newConfig.name || `模型 ${configs.length + 1}`,
      base_url: newConfig.base_url || 'https://ark.cn-beijing.volces.com/api/v3',
      api_key: newConfig.api_key,
      model_name: newConfig.model_name,
      display_name: newConfig.display_name || newConfig.name || `模型 ${configs.length + 1}`,
      is_default: configs.length === 0
    };
    
    const updated = [...configs, newConfigEntry];
    saveConfigs(updated);
    setNewConfig({
      name: '',
      base_url: '',
      api_key: '',
      model_name: '',
      display_name: ''
    });
    setShowNewForm(false);
  };

  const deleteConfig = (index) => {
    if (configs.length <= 1) return;
    const updated = configs.filter((_, i) => i !== index);
    saveConfigs(updated);
    setTestResults(prev => {
      const newResults = {};
      Object.keys(prev).forEach(k => {
        const ki = parseInt(k);
        if (ki < index) newResults[ki] = prev[k];
        else if (ki > index) newResults[ki - 1] = prev[k];
      });
      return newResults;
    });
  };

  const toggleDefault = (index) => {
    const updated = configs.map((c, i) => ({
      ...c,
      is_default: i === index
    }));
    saveConfigs(updated);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-600/20 rounded-lg">
            <Settings className="w-5 h-5 text-primary-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">LLM 模型配置</h2>
            <p className="text-sm text-slate-400">配置 OpenAI 兼容的 API 设置，支持多模型切换</p>
          </div>
        </div>
        <button
          onClick={() => setShowNewForm(!showNewForm)}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {showNewForm ? '取消' : '+ 添加配置'}
        </button>
      </div>

      {showNewForm && (
        <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700">
          <h3 className="text-sm font-medium text-slate-200 mb-4">新配置</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">配置名称</label>
              <input
                type="text"
                value={newConfig.name}
                onChange={(e) => setNewConfig({ ...newConfig, name: e.target.value })}
                placeholder="例如：GPT-4"
                className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">显示名称</label>
              <input
                type="text"
                value={newConfig.display_name}
                onChange={(e) => setNewConfig({ ...newConfig, display_name: e.target.value })}
                placeholder="例如：GPT-4 模型"
                className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-primary-500"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm text-slate-400 mb-1">
                <Globe className="w-4 h-4 inline mr-1" />
                API Base URL
              </label>
              <input
                type="text"
                value={newConfig.base_url}
                onChange={(e) => setNewConfig({ ...newConfig, base_url: e.target.value })}
                placeholder="https://api.openai.com/v1 或 https://ark.cn-beijing.volces.com/api/v3"
                className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-primary-500"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm text-slate-400 mb-1">
                <Key className="w-4 h-4 inline mr-1" />
                API Key
              </label>
              <div className="relative">
                <input
                  type={showApiKey.new ? 'text' : 'password'}
                  value={newConfig.api_key}
                  onChange={(e) => setNewConfig({ ...newConfig, api_key: e.target.value })}
                  placeholder="sk-..."
                  className="w-full px-3 py-2 pr-10 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-primary-500"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(prev => ({ ...prev, new: !prev.new }))}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-300"
                >
                  {showApiKey.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm text-slate-400 mb-1">
                <Cpu className="w-4 h-4 inline mr-1" />
                Model Name
              </label>
              <input
                type="text"
                value={newConfig.model_name}
                onChange={(e) => setNewConfig({ ...newConfig, model_name: e.target.value })}
                placeholder="例如：gpt-4 或 doubao-seed-1.8b-chat"
                className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-primary-500"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button
              onClick={() => setShowNewForm(false)}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm transition-colors"
            >
              取消
            </button>
            <button
              onClick={addNewConfig}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm transition-colors"
            >
              添加配置
            </button>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {configs.map((config, index) => (
          <div
            key={config.id}
            className={`p-4 bg-slate-800/50 rounded-xl border transition-all ${
              config.is_default 
                ? 'border-primary-500/50 ring-1 ring-primary-500/20' 
                : 'border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${config.is_default ? 'bg-primary-500' : 'bg-slate-500'}`} />
                <div>
                  <h3 className="text-sm font-medium text-slate-100">{config.display_name || config.name}</h3>
                  <p className="text-xs text-slate-500">{config.model_name}</p>
                </div>
                {config.is_default && (
                  <span className="px-2 py-0.5 bg-primary-600/20 text-primary-400 text-xs rounded-full">
                    默认
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleDefault(index)}
                  className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                    config.is_default
                      ? 'bg-slate-700 text-slate-400 cursor-default'
                      : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  }`}
                  disabled={config.is_default}
                >
                  设为默认
                </button>
                {configs.length > 1 && (
                  <button
                    onClick={() => deleteConfig(index)}
                    className="p-1.5 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                  >
                    <AlertCircle className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-xs text-slate-500 mb-1">API Base URL</label>
                <input
                  type="text"
                  value={config.base_url}
                  onChange={(e) => updateConfigField(index, 'base_url', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700/30 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-primary-500"
                />
              </div>
              
              <div className="md:col-span-2">
                <label className="block text-xs text-slate-500 mb-1">API Key</label>
                <div className="relative">
                  <input
                    type={showApiKey[index] ? 'text' : 'password'}
                    value={config.api_key}
                    onChange={(e) => updateConfigField(index, 'api_key', e.target.value)}
                    className="w-full px-3 py-2 pr-10 bg-slate-700/30 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-primary-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(prev => ({ ...prev, [index]: !prev[index] }))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-300"
                  >
                    {showApiKey[index] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs text-slate-500 mb-1">Model Name</label>
                <input
                  type="text"
                  value={config.model_name}
                  onChange={(e) => updateConfigField(index, 'model_name', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700/30 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs text-slate-500 mb-1">显示名称</label>
                <input
                  type="text"
                  value={config.display_name || config.name}
                  onChange={(e) => updateConfigField(index, 'display_name', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700/30 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-primary-500"
                />
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between">
              <button
                onClick={() => testConnection(index)}
                disabled={testing[index]}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-300 rounded-lg text-sm transition-colors"
              >
                {testing[index] ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4" />
                )}
                {testing[index] ? '测试中...' : '测试连接'}
              </button>
              
              {testResults[index] && (
                <div className={`flex items-center gap-2 text-sm ${
                  testResults[index].success ? 'text-green-400' : 'text-red-400'
                }`}>
                  {testResults[index].success ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    <AlertCircle className="w-4 h-4" />
                  )}
                  {testResults[index].message}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {configs.length === 0 && !showNewForm && (
        <div className="text-center py-12 text-slate-400">
          <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>暂无配置，点击上方按钮添加第一个模型配置</p>
        </div>
      )}

      <div className="p-4 bg-slate-800/30 rounded-xl border border-slate-700/50">
        <h4 className="text-sm font-medium text-slate-200 mb-2">支持的 API 格式</h4>
        <ul className="text-xs text-slate-400 space-y-1">
          <li>• OpenAI 官方 API: <code className="text-slate-300">https://api.openai.com/v1</code></li>
          <li>• 火山方舟: <code className="text-slate-300">https://ark.cn-beijing.volces.com/api/v3</code></li>
          <li>• 任何 OpenAI 兼容的 API 服务</li>
        </ul>
      </div>
    </div>
  );
}
