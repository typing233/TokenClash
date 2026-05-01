import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useArenaStore } from '../../store';
import socketService from '../../services/socket';
import { arenaApi, modelsApi } from '../../services/api';
import { Clock, Users, Zap, Shield, Heart, Snowflake, TrendingUp, ChevronLeft, Play, AlertCircle, Loader2, Trophy } from 'lucide-react';
import EnergyBar from './EnergyBar';
import SkillCard from './SkillCard';
import ArenaCountdown from './ArenaCountdown';

const SKILLS = [
  {
    skill_id: 'lightning',
    name: '雷击',
    description: '对目标造成20点能量伤害',
    icon: Zap,
    color: '#ff6b6b',
    cost: 15
  },
  {
    skill_id: 'shield',
    name: '护盾',
    description: '为目标添加护盾，免疫伤害',
    icon: Shield,
    color: '#4ecdc4',
    cost: 20
  },
  {
    skill_id: 'energy_boost',
    name: '充能',
    description: '为目标恢复30点能量',
    icon: Heart,
    color: '#ffe66d',
    cost: 10
  },
  {
    skill_id: 'vote_multiplier',
    name: '投票增幅',
    description: '目标获得的票数变为2倍',
    icon: TrendingUp,
    color: '#a78bfa',
    cost: 25
  },
  {
    skill_id: 'freeze',
    name: '冰冻',
    description: '冻结目标5秒',
    icon: Snowflake,
    color: '#74b9ff',
    cost: 20
  }
];

const STAGE_NAMES = {
  waiting: '等待开始',
  countdown: '倒计时',
  active: '激烈对决',
  voting: '最终投票',
  judging: 'AI裁判判定中',
  finished: '比赛结束'
};

export default function ArenaLive() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [room, setRoom] = useState(null);
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [skillEffects, setSkillEffects] = useState([]);
  const [hasVoted, setHasVoted] = useState(false);
  
  const {
    countdown,
    energy,
    votes,
    setCurrentRoom,
    updateEnergy,
    updateVote,
    addSkillEffect,
    clearRoom
  } = useArenaStore(state => ({
    countdown: state.countdown,
    energy: state.energy,
    votes: state.votes,
    setCurrentRoom: state.setCurrentRoom,
    updateEnergy: state.updateEnergy,
    updateVote: state.updateVote,
    addSkillEffect: state.addSkillEffect,
    clearRoom: state.clearRoom
  }));

  useEffect(() => {
    const loadRoom = async () => {
      try {
        setLoading(true);
        setError(null);
        
        socketService.connect();
        
        const response = await arenaApi.getRoom(roomId);
        const roomData = response.data;
        
        setRoom(roomData);
        setCurrentRoom(roomData);
        
        socketService.socket.emit('join_arena', { room_id: roomId });
        
      } catch (err) {
        console.error('Failed to load arena room:', err);
        setError(err.response?.data?.detail || '加载竞技场房间失败');
      } finally {
        setLoading(false);
      }
    };
    
    loadRoom();
    
    return () => {
      socketService.socket.emit('leave_arena', { room_id: roomId });
      clearRoom();
    };
  }, [roomId, setCurrentRoom, clearRoom]);

  useEffect(() => {
    const unsubscribers = [];
    
    const handleCountdownUpdate = (data) => {
      useArenaStore.setState({ countdown: data.countdown_remaining });
    };
    unsubscribers.push(socketService.on('countdown_update', handleCountdownUpdate));
    
    const handleEnergyUpdated = (data) => {
      updateEnergy(data.model_id, data.added);
    };
    unsubscribers.push(socketService.on('energy_updated', handleEnergyUpdated));
    
    const handleVoteCast = (data) => {
      updateVote(data.model_id, data.multiplied ? 2 : 1);
    };
    unsubscribers.push(socketService.on('vote_cast', handleVoteCast));
    
    const handleSkillUsed = (data) => {
      setSkillEffects(prev => [...prev.slice(-5), data]);
      addSkillEffect(data);
    };
    unsubscribers.push(socketService.on('skill_used', handleSkillUsed));
    
    const handleStageChange = (data) => {
      setRoom(prev => prev ? { ...prev, stage: data.stage } : null);
    };
    unsubscribers.push(socketService.on('stage_change', handleStageChange));
    
    const handleArenaResult = (data) => {
      setRoom(prev => prev ? {
        ...prev,
        stage: 'finished',
        winner: data.winner_model_id,
        winner_display_name: data.winner_display_name,
        final_scores: data.details
      } : null);
    };
    unsubscribers.push(socketService.on('arena_result', handleArenaResult));
    
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
    };
  }, [updateEnergy, updateVote, addSkillEffect]);

  const handleStartRoom = async () => {
    try {
      await arenaApi.startRoom(roomId);
    } catch (err) {
      console.error('Failed to start room:', err);
    }
  };

  const handleUseSkill = async (skillId) => {
    if (!selectedTarget) return;
    
    try {
      await arenaApi.useSkill(roomId, {
        skill_id: skillId,
        target_model_id: selectedTarget
      });
    } catch (err) {
      console.error('Failed to use skill:', err);
    }
  };

  const handleVote = async (modelId) => {
    if (hasVoted) return;
    
    try {
      await arenaApi.castVote(roomId, { model_id: modelId });
      setHasVoted(true);
    } catch (err) {
      console.error('Failed to vote:', err);
    }
  };

  const handleAddEnergy = async (modelId, amount = 10) => {
    try {
      await arenaApi.addEnergy(roomId, { model_id: modelId, amount });
    } catch (err) {
      console.error('Failed to add energy:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-900">
        <div className="text-center">
          <Loader2 className="w-12 h-12 mx-auto mb-4 text-primary-500 animate-spin" />
          <p className="text-slate-400">加载竞技场中...</p>
        </div>
      </div>
    );
  }

  if (error || !room) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-slate-900">
        <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
        <p className="text-slate-300 mb-4">{error || '房间不存在'}</p>
        <button
          onClick={() => navigate('/')}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition-colors"
        >
          返回首页
        </button>
      </div>
    );
  }

  const participants = room.participants || [];
  const p1 = participants[0];
  const p2 = participants[1];
  const isFinished = room.stage === 'finished';

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* 顶部信息栏 */}
      <div className="bg-slate-800/90 backdrop-blur-sm border-b border-slate-700 px-4 py-3">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-300"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            
            <div>
              <h1 className="text-lg font-semibold text-slate-100">{room.title}</h1>
              <div className="flex items-center gap-3 text-sm text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {STAGE_NAMES[room.stage] || room.stage}
                </span>
                {room.viewer_count > 0 && (
                  <span className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    {room.viewer_count} 观众
                  </span>
                )}
              </div>
            </div>
          </div>
          
          {room.stage === 'waiting' && (
            <button
              onClick={handleStartRoom}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Play className="w-4 h-4" />
              开始对决
            </button>
          )}
        </div>
      </div>

      {/* 倒计时显示 */}
      {(room.stage === 'active' || room.stage === 'countdown') && (
        <ArenaCountdown 
          current={countdown || room.countdown_remaining} 
          total={room.total_countdown} 
        />
      )}

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col p-4 max-w-6xl mx-auto w-full">
        {isFinished ? (
          /* 比赛结束结果展示 */
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="text-center mb-8">
              <Trophy className="w-20 h-20 mx-auto mb-4 text-yellow-400" />
              <h2 className="text-3xl font-bold text-yellow-400 mb-2">
                {room.winner_display_name} 获胜！
              </h2>
              <p className="text-slate-400">比赛结束</p>
            </div>
            
            {room.final_scores && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-2xl">
                {Object.entries(room.final_scores).map(([key, data]) => (
                  <div 
                    key={key}
                    className={`p-6 rounded-xl border ${
                      data.model_id === room.winner 
                        ? 'bg-yellow-500/10 border-yellow-500/30' 
                        : 'bg-slate-800/50 border-slate-700'
                    }`}
                  >
                    <h3 className={`text-lg font-semibold mb-4 ${
                      data.model_id === room.winner ? 'text-yellow-400' : 'text-slate-200'
                    }`}>
                      {data.display_name}
                      {data.model_id === room.winner && ' 👑'}
                    </h3>
                    
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400">能量值</span>
                        <span className="text-slate-200">{data.energy}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400">票数</span>
                        <span className="text-slate-200">{data.votes}</span>
                      </div>
                      <div className="border-t border-slate-700 pt-3 mt-3">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-400">综合得分</span>
                          <span className="text-primary-400 font-semibold">
                            {(data.scores?.total * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* 对决进行中 */
          <div className="flex-1 flex flex-col gap-4">
            {/* 双方对决区域 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {p1 && (
                <div 
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    selectedTarget === p1.model_id 
                      ? 'bg-green-600/10 border-green-500 ring-2 ring-green-500/30' 
                      : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
                  }`}
                  onClick={() => setSelectedTarget(selectedTarget === p1.model_id ? null : p1.model_id)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-10 h-10 rounded-full bg-green-600/30 flex items-center justify-center">
                        <span className="text-green-400 font-bold">正</span>
                      </div>
                      <div>
                        <h3 className="text-sm font-medium text-green-400">{p1.display_name}</h3>
                        <p className="text-xs text-slate-500">正方</p>
                      </div>
                    </div>
                    {p1.is_frozen && (
                      <Snowflake className="w-5 h-5 text-cyan-400 animate-pulse" />
                    )}
                  </div>
                  
                  <EnergyBar 
                    current={energy[p1.model_id] || p1.energy || 100} 
                    max={p1.max_energy || 100}
                    color="green"
                    label="能量"
                  />
                  
                  <div className="mt-3 flex items-center justify-between text-sm">
                    <span className="text-slate-400">票数</span>
                    <span className="text-slate-200 font-semibold">
                      {votes[p1.model_id] || p1.votes || 0}
                    </span>
                  </div>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAddEnergy(p1.model_id);
                    }}
                    className="mt-3 w-full px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 text-green-400 rounded-lg text-xs transition-colors"
                  >
                    +10 能量
                  </button>
                </div>
              )}
              
              {/* VS 区域 */}
              <div className="flex flex-col items-center justify-center">
                <div className="text-4xl font-bold text-slate-600 mb-2">VS</div>
                
                {!isFinished && (room.stage === 'active' || room.stage === 'voting') && (
                  <div className="text-center">
                    <p className="text-xs text-slate-500 mb-2">
                      {room.stage === 'voting' ? '请投票支持您喜欢的模型' : '选择目标使用技能'}
                    </p>
                    
                    {room.stage === 'voting' && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => p1 && handleVote(p1.model_id)}
                          disabled={hasVoted}
                          className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm transition-colors"
                        >
                          支持正方
                        </button>
                        <button
                          onClick={() => p2 && handleVote(p2.model_id)}
                          disabled={hasVoted}
                          className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm transition-colors"
                        >
                          支持反方
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {p2 && (
                <div 
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    selectedTarget === p2.model_id 
                      ? 'bg-red-600/10 border-red-500 ring-2 ring-red-500/30' 
                      : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
                  }`}
                  onClick={() => setSelectedTarget(selectedTarget === p2.model_id ? null : p2.model_id)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-10 h-10 rounded-full bg-red-600/30 flex items-center justify-center">
                        <span className="text-red-400 font-bold">反</span>
                      </div>
                      <div>
                        <h3 className="text-sm font-medium text-red-400">{p2.display_name}</h3>
                        <p className="text-xs text-slate-500">反方</p>
                      </div>
                    </div>
                    {p2.is_frozen && (
                      <Snowflake className="w-5 h-5 text-cyan-400 animate-pulse" />
                    )}
                  </div>
                  
                  <EnergyBar 
                    current={energy[p2.model_id] || p2.energy || 100} 
                    max={p2.max_energy || 100}
                    color="red"
                    label="能量"
                  />
                  
                  <div className="mt-3 flex items-center justify-between text-sm">
                    <span className="text-slate-400">票数</span>
                    <span className="text-slate-200 font-semibold">
                      {votes[p2.model_id] || p2.votes || 0}
                    </span>
                  </div>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAddEnergy(p2.model_id);
                    }}
                    className="mt-3 w-full px-3 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg text-xs transition-colors"
                  >
                    +10 能量
                  </button>
                </div>
              )}
            </div>

            {/* 技能卡区域 */}
            {room.stage === 'active' && (
              <div className="mt-auto">
                <h4 className="text-sm font-medium text-slate-400 mb-3">技能卡 (先点击选择目标，再点击技能)</h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                  {SKILLS.map(skill => (
                    <SkillCard
                      key={skill.skill_id}
                      skill={skill}
                      selectedTarget={selectedTarget}
                      onUse={() => handleUseSkill(skill.skill_id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* 技能效果日志 */}
            {skillEffects.length > 0 && (
              <div className="mt-4 p-3 bg-slate-800/30 rounded-lg max-h-24 overflow-y-auto">
                <div className="space-y-1">
                  {skillEffects.slice(-5).map((effect, i) => (
                    <div key={i} className="text-xs text-slate-400 flex items-center gap-2">
                      <span className="text-slate-500">[{new Date().toLocaleTimeString('zh-CN')}]</span>
                      <span 
                        className={effect.effect_applied ? 'text-green-400' : 'text-slate-500'}
                      >
                        {effect.effect_message}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
