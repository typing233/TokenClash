import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { topicsApi, modelsApi, debatesApi } from '../../services/api';
import { Plus, TrendingUp, Clock, MessageSquare, Play, Swords } from 'lucide-react';

const TopicsPage = () => {
  const [loading, setLoading] = useState(true);
  const [topics, setTopics] = useState([]);
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [showCreateDebate, setShowCreateDebate] = useState(false);
  const [selectedModels, setSelectedModels] = useState({ affirmative: null, negative: null });
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        // 加载话题列表
        const topicsResponse = await topicsApi.getList({ limit: 20 });
        setTopics(topicsResponse.data.topics || []);
        
        // 加载可用模型
        const modelsResponse = await modelsApi.getList();
        setAvailableModels(modelsResponse.data.models || []);
        
      } catch (err) {
        console.error('Failed to load topics:', err);
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, []);

  const handleStartDebate = async () => {
    if (!selectedTopic || !selectedModels.affirmative || !selectedModels.negative) {
      setError('请选择话题和两个模型');
      return;
    }
    
    if (selectedModels.affirmative === selectedModels.negative) {
      setError('正方和反方不能是同一个模型');
      return;
    }
    
    try {
      setCreating(true);
      setError(null);
      
      const response = await debatesApi.create({
        topic_id: selectedTopic._id,
        title: selectedTopic.title,
        category: selectedTopic.category || 'general',
        participants: [
          { model_id: selectedModels.affirmative.model_id, side: 'affirmative' },
          { model_id: selectedModels.negative.model_id, side: 'negative' }
        ],
        config: {
          opening_rounds: 1,
          cross_rounds: 2,
          closing_rounds: 1
        }
      });
      
      // 自动开始辩论
      await debatesApi.start(response.data._id);
      
      // 跳转到辩论页面
      window.location.href = `/debates/${response.data._id}`;
      
    } catch (err) {
      console.error('Failed to create debate:', err);
      setError(err.response?.data?.detail || '创建辩论失败');
    } finally {
      setCreating(false);
    }
  };

  const handleModelSelect = (side, model) => {
    setSelectedModels(prev => ({
      ...prev,
      [side]: model
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="loading-spinner w-10 h-10 mx-auto mb-4" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">话题广场</h1>
          <p className="text-slate-400 mt-1">选择一个话题开始AI辩论</p>
        </div>
        <Link
          to="/topics/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl font-medium transition-all"
        >
          <Plus className="w-5 h-5" />
          发起新话题
        </Link>
      </div>
      
      {/* 话题列表 */}
      <div className="space-y-4">
        {topics.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>暂无话题</p>
            <Link
              to="/topics/new"
              className="inline-flex items-center gap-2 px-4 py-2 mt-4 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-medium transition-all"
            >
              <Plus className="w-5 h-5" />
              发起第一个话题
            </Link>
          </div>
        ) : (
          topics.map(topic => (
            <div
              key={topic._id}
              className={`p-4 rounded-xl transition-all cursor-pointer ${
                selectedTopic?._id === topic._id
                  ? 'bg-primary-600/10 border border-primary-500/30'
                  : 'bg-slate-800/30 hover:bg-slate-800/50 border border-transparent'
              }`}
              onClick={() => setSelectedTopic(topic)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h3 className="font-medium text-slate-100 text-lg">
                    {topic.title}
                  </h3>
                  {topic.description && (
                    <p className="text-sm text-slate-400 mt-1 line-clamp-2">
                      {topic.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-4">
                  {topic.category && (
                    <span className="px-2 py-1 text-xs bg-slate-700/50 text-slate-400 rounded-full">
                      {topic.category}
                    </span>
                  )}
                  {topic.is_auto_generated && (
                    <span className="px-2 py-1 text-xs bg-orange-500/10 text-orange-400 rounded-full">
                      热门话题
                    </span>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-4 text-xs text-slate-500">
                {topic.tags && topic.tags.length > 0 && (
                  <div className="flex items-center gap-1">
                    {topic.tags.slice(0, 3).map((tag, idx) => (
                      <span key={idx} className="text-slate-500">
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {new Date(topic.created_at).toLocaleDateString('zh-CN')}
                </span>
              </div>
              
              {/* 模型选择面板 */}
              {selectedTopic?._id === topic._id && (
                <div className="mt-4 pt-4 border-t border-slate-700/50">
                  <h4 className="text-sm font-medium text-slate-300 mb-3">
                    选择对战模型
                  </h4>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* 正方模型选择 */}
                    <div className="space-y-2">
                      <label className="text-xs text-green-400 font-medium">正方</label>
                      <div className="grid grid-cols-1 gap-2">
                        {availableModels.map(model => (
                          <button
                            key={`affirmative-${model.model_id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleModelSelect('affirmative', model);
                            }}
                            className={`p-3 rounded-lg text-left transition-all ${
                              selectedModels.affirmative?.model_id === model.model_id
                                ? 'bg-green-600/20 border border-green-500/30'
                                : 'bg-slate-700/30 hover:bg-slate-700/50 border border-transparent'
                            }`}
                          >
                            <span className={`text-sm ${
                              selectedModels.affirmative?.model_id === model.model_id
                                ? 'text-green-400'
                                : 'text-slate-300'
                            }`}>
                              {model.display_name}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    {/* VS */}
                    <div className="flex items-center justify-center">
                      <div className="flex flex-col items-center gap-2">
                        <Swords className="w-8 h-8 text-slate-500" />
                        <span className="text-sm text-slate-500">VS</span>
                      </div>
                    </div>
                    
                    {/* 反方模型选择 */}
                    <div className="space-y-2">
                      <label className="text-xs text-red-400 font-medium">反方</label>
                      <div className="grid grid-cols-1 gap-2">
                        {availableModels.map(model => (
                          <button
                            key={`negative-${model.model_id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleModelSelect('negative', model);
                            }}
                            className={`p-3 rounded-lg text-left transition-all ${
                              selectedModels.negative?.model_id === model.model_id
                                ? 'bg-red-600/20 border border-red-500/30'
                                : 'bg-slate-700/30 hover:bg-slate-700/50 border border-transparent'
                            }`}
                          >
                            <span className={`text-sm ${
                              selectedModels.negative?.model_id === model.model_id
                                ? 'text-red-400'
                                : 'text-slate-300'
                            }`}>
                              {model.display_name}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  {/* 错误提示 */}
                  {error && (
                    <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                      {error}
                    </div>
                  )}
                  
                  {/* 开始辩论按钮 */}
                  <div className="mt-4 flex justify-end">
                    <button
                      onClick={handleStartDebate}
                      disabled={creating || !selectedModels.affirmative || !selectedModels.negative}
                      className={`inline-flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
                        creating || !selectedModels.affirmative || !selectedModels.negative
                          ? 'bg-slate-600 cursor-not-allowed text-slate-400'
                          : 'bg-primary-600 hover:bg-primary-500 text-white'
                      }`}
                    >
                      {creating ? (
                        <>
                          <div className="loading-spinner w-5 h-5 border-slate-400 border-t-primary-500" />
                          <span>创建中...</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-5 h-5" />
                          <span>开始辩论</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TopicsPage;
