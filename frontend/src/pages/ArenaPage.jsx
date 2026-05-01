import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { arenaApi, modelsApi } from '../services/api';
import { useModelStore } from '../store';
import { Plus, Swords, Users, Clock, Play, Loader2, X, Settings2 } from 'lucide-react';

export default function ArenaPage() {
  const navigate = useNavigate();
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  const [models, setModels] = useState([]);
  const [createLoading, setCreateLoading] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: '',
    participant1: '',
    participant2: ''
  });

  const modelConfigs = useModelStore(state => state.modelConfigs);

  useEffect(() => {
    loadRooms();
    loadModels();
    
    const interval = setInterval(loadRooms, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadRooms = async () => {
    try {
      const response = await arenaApi.getRooms();
      setRooms(response.data || []);
    } catch (err) {
      console.error('Failed to load rooms:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async () => {
    try {
      const response = await modelsApi.getConfiguredModels();
      const configured = response.data || [];
      
      const modelsList = configured.map(config => ({
        id: config.model_id,
        name: config.display_name,
        model_id: config.model_id
      }));
      
      setAvailableModels(modelsList);
      setModels(modelsList);
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const handleCreateRoom = async (e) => {
    e.preventDefault();
    
    if (!createForm.title || !createForm.participant1 || !createForm.participant2) {
      return;
    }
    
    if (createForm.participant1 === createForm.participant2) {
      alert('请选择两个不同的模型');
      return;
    }
    
    try {
      setCreateLoading(true);
      
      const model1 = models.find(m => m.id === createForm.participant1);
      const model2 = models.find(m => m.id === createForm.participant2);
      
      const response = await arenaApi.createRoom({
        title: createForm.title,
        participants: [
          { model_id: createForm.participant1, display_name: model1?.name || createForm.participant1 },
          { model_id: createForm.participant2, display_name: model2?.name || createForm.participant2 }
        ]
      });
      
      setShowCreateModal(false);
      setCreateForm({ title: '', participant1: '', participant2: '' });
      
      navigate(`/arena/${response.data.room_id}`);
      
    } catch (err) {
      console.error('Failed to create room:', err);
      alert('创建房间失败: ' + (err.response?.data?.detail || '未知错误'));
    } finally {
      setCreateLoading(false);
    }
  };

  const handleJoinRoom = (roomId) => {
    navigate(`/arena/${roomId}`);
  };

  const getStageDisplay = (stage) => {
    const stages = {
      waiting: { text: '等待开始', color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
      countdown: { text: '倒计时', color: 'text-blue-400', bg: 'bg-blue-400/10' },
      active: { text: '对决中', color: 'text-green-400', bg: 'bg-green-400/10' },
      voting: { text: '投票中', color: 'text-purple-400', bg: 'bg-purple-400/10' },
      judging: { text: '判定中', color: 'text-orange-400', bg: 'bg-orange-400/10' },
      finished: { text: '已结束', color: 'text-slate-400', bg: 'bg-slate-400/10' }
    };
    return stages[stage] || stages.waiting;
  };

  return (
    <div className="min-h-screen bg-slate-900">
      {/* 头部 */}
      <div className="bg-slate-800/50 border-b border-slate-700">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-primary-600/20 rounded-xl">
                <Swords className="w-6 h-6 text-primary-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-100">竞技场</h1>
                <p className="text-sm text-slate-400">两个AI模型的终极对决</p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate('/models')}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm transition-colors"
              >
                <Settings2 className="w-4 h-4" />
                配置模型
              </button>
              
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <Plus className="w-4 h-4" />
                创建房间
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 房间列表 */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
          </div>
        ) : rooms.length === 0 ? (
          <div className="text-center py-12">
            <div className="p-4 bg-slate-800/50 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <Swords className="w-8 h-8 text-slate-600" />
            </div>
            <h3 className="text-lg font-medium text-slate-300 mb-2">暂无房间</h3>
            <p className="text-slate-500 mb-4">点击"创建房间"开始第一场对决</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-colors mx-auto"
            >
              <Plus className="w-4 h-4" />
              创建房间
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {rooms.map(room => {
              const stage = getStageDisplay(room.stage);
              const participants = room.participants || [];
              const p1 = participants[0];
              const p2 = participants[1];
              
              return (
                <div
                  key={room.room_id}
                  onClick={() => handleJoinRoom(room.room_id)}
                  className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 hover:border-primary-500/50 transition-all cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-slate-200 truncate">{room.title}</h3>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${stage.bg} ${stage.color}`}>
                      {stage.text}
                    </span>
                  </div>
                  
                  {/* 对战双方 */}
                  <div className="flex items-center justify-between py-3">
                    <div className="text-center flex-1">
                      <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-green-600/30 flex items-center justify-center">
                        <span className="text-green-400 text-sm font-bold">正</span>
                      </div>
                      <p className="text-sm text-slate-300 truncate">
                        {p1?.display_name || p1?.model_id || '模型1'}
                      </p>
                    </div>
                    
                    <div className="text-slate-600 font-bold text-sm px-4">VS</div>
                    
                    <div className="text-center flex-1">
                      <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-red-600/30 flex items-center justify-center">
                        <span className="text-red-400 text-sm font-bold">反</span>
                      </div>
                      <p className="text-sm text-slate-300 truncate">
                        {p2?.display_name || p2?.model_id || '模型2'}
                      </p>
                    </div>
                  </div>
                  
                  {/* 房间信息 */}
                  <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-700/50">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        {room.viewer_count || 0} 观众
                      </span>
                      {room.countdown_remaining && room.stage === 'active' && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {room.countdown_remaining}s
                        </span>
                      )}
                    </div>
                    
                    <span className="text-primary-400 group-hover:text-primary-300 transition-colors">
                      进入 →
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 创建房间模态框 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b border-slate-700">
              <h2 className="text-lg font-semibold text-slate-100">创建对战房间</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 hover:bg-slate-700 rounded-lg transition-colors text-slate-400"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleCreateRoom} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  房间标题
                </label>
                <input
                  type="text"
                  value={createForm.title}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="例如：GPT-4 vs Claude"
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  正方模型
                </label>
                <select
                  value={createForm.participant1}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, participant1: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  required
                >
                  <option value="">选择模型...</option>
                  {models.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name || model.id}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  反方模型
                </label>
                <select
                  value={createForm.participant2}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, participant2: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  required
                >
                  <option value="">选择模型...</option>
                  {models.map(model => (
                    <option 
                      key={model.id} 
                      value={model.id}
                      disabled={model.id === createForm.participant1}
                    >
                      {model.name || model.id}
                      {model.id === createForm.participant1 && ' (已选择)'}
                    </option>
                  ))}
                </select>
              </div>
              
              {models.length === 0 && (
                <p className="text-sm text-yellow-400/80 bg-yellow-400/10 px-3 py-2 rounded-lg">
                  请先在"配置模型"中添加至少2个模型
                </p>
              )}
              
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={createLoading || models.length < 2}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
                >
                  {createLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Swords className="w-4 h-4" />
                  )}
                  创建房间
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
