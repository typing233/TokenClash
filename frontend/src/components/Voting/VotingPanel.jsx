import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { votesApi, debatesApi } from '../../services/api';
import { ThumbsUp, ThumbsDown, Brain, Heart, Laugh, CheckCircle } from 'lucide-react';

const VotingPanel = ({ debate, onVoteSubmit }) => {
  const [voting, setVoting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);
  
  // 评分状态
  const [logicScores, setLogicScores] = useState({});
  const [persuasionScores, setPersuasionScores] = useState({});
  const [humorScores, setHumorScores] = useState({});
  const [preferredModel, setPreferredModel] = useState(null);
  
  // 投票结果
  const [voteResult, setVoteResult] = useState(null);
  const [loadingResult, setLoadingResult] = useState(false);

  const participants = debate?.participants || [];
  
  // 初始化评分
  useEffect(() => {
    const initialLogic = {};
    const initialPersuasion = {};
    const initialHumor = {};
    
    participants.forEach(p => {
      initialLogic[p.model_id] = 5;
      initialPersuasion[p.model_id] = 5;
      initialHumor[p.model_id] = 5;
    });
    
    setLogicScores(initialLogic);
    setPersuasionScores(initialPersuasion);
    setHumorScores(initialHumor);
  }, [participants]);

  // 获取投票结果
  const loadVoteResult = async () => {
    if (!debate?._id) return;
    
    try {
      setLoadingResult(true);
      const response = await votesApi.getResult(debate._id);
      setVoteResult(response.data);
    } catch (err) {
      console.error('Failed to load vote result:', err);
    } finally {
      setLoadingResult(false);
    }
  };

  const handleSubmitVote = async () => {
    if (!preferredModel) {
      setError('请选择您支持的辩手');
      return;
    }
    
    try {
      setVoting(true);
      setError(null);
      
      await votesApi.create({
        debate_id: debate._id,
        logic_score: logicScores,
        persuasion_score: persuasionScores,
        humor_score: humorScores,
        preferred_model_id: preferredModel,
        user_id: null, // 可选，用户ID
        user_name: '匿名观众',
        comment: ''
      });
      
      setSubmitted(true);
      
      // 重新加载投票结果
      await loadVoteResult();
      
      if (onVoteSubmit) {
        onVoteSubmit();
      }
      
    } catch (err) {
      setError(err.response?.data?.detail || '投票失败');
    } finally {
      setVoting(false);
    }
  };

  const getParticipantByModelId = (modelId) => {
    return participants.find(p => p.model_id === modelId);
  };

  // 渲染评分滑块
  const renderScoreSlider = (scores, setScores, label, icon) => {
    const Icon = icon;
    return (
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Icon className="w-5 h-5 text-primary-400" />
          <span className="font-medium text-slate-200">{label}</span>
        </div>
        
        <div className="space-y-4">
          {participants.map(participant => {
            const score = scores[participant.model_id] || 5;
            const isAffirmative = participant.side === 'affirmative';
            
            return (
              <div key={participant.model_id} className="flex items-center gap-4">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  isAffirmative ? 'bg-green-600/30' : 'bg-red-600/30'
                }`}>
                  <span className={`text-sm font-bold ${
                    isAffirmative ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {isAffirmative ? '正' : '反'}
                  </span>
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-300">{participant.display_name}</span>
                    <span className={`text-sm font-bold ${
                      score >= 7 ? 'text-green-400' : score >= 5 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {score}/10
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={score}
                    onChange={(e) => setScores(prev => ({
                      ...prev,
                      [participant.model_id]: parseInt(e.target.value)
                    }))}
                    className="vote-slider w-full"
                    disabled={submitted}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // 渲染投票结果
  const renderVoteResult = () => {
    if (!voteResult) return null;
    
    const winner = getParticipantByModelId(voteResult.winner_model_id);
    
    return (
      <div className="mt-6 p-4 bg-slate-700/50 rounded-xl">
        <h3 className="text-lg font-semibold text-center mb-4 text-slate-100">
          投票结果
        </h3>
        
        {winner && (
          <div className="text-center mb-4">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 rounded-full border border-yellow-500/30">
              <CheckCircle className="w-5 h-5 text-yellow-400" />
              <span className="text-yellow-400 font-medium">
                {winner.display_name} 获胜！
              </span>
            </div>
          </div>
        )}
        
        <div className="space-y-4">
          {participants.map(participant => {
            const modelId = participant.model_id;
            const isAffirmative = participant.side === 'affirmative';
            const isWinner = modelId === voteResult.winner_model_id;
            
            return (
              <div key={modelId} className={`p-3 rounded-lg ${
                isWinner ? 'bg-yellow-500/10 border border-yellow-500/30' : 'bg-slate-700/30'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                      isAffirmative ? 'bg-green-600/30' : 'bg-red-600/30'
                    }`}>
                      <span className={`text-xs font-bold ${
                        isAffirmative ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {isAffirmative ? '正' : '反'}
                      </span>
                    </div>
                    <span className="font-medium text-slate-200">{participant.display_name}</span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {voteResult.preference_counts[modelId] || 0} 票
                  </span>
                </div>
                
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="text-center">
                    <div className="text-slate-400">逻辑</div>
                    <div className="font-medium text-slate-200">
                      {voteResult.logic_averages[modelId]?.toFixed(1) || '-'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-slate-400">说服力</div>
                    <div className="font-medium text-slate-200">
                      {voteResult.persuasion_averages[modelId]?.toFixed(1) || '-'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-slate-400">综合</div>
                    <div className="font-medium text-slate-200">
                      {voteResult.overall_scores[modelId]?.toFixed(1) || '-'}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        
        <div className="mt-4 text-center text-sm text-slate-500">
          共 {voteResult.total_votes} 人参与投票
        </div>
      </div>
    );
  };

  if (submitted || voteResult) {
    return (
      <div className="max-w-lg mx-auto p-4">
        <div className="text-center mb-4">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-600/20 rounded-full text-green-400">
            <CheckCircle className="w-5 h-5" />
            <span>投票成功！</span>
          </div>
        </div>
        
        {renderVoteResult()}
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto p-4">
      <h2 className="text-xl font-bold text-center mb-6 text-slate-100">
        投票评分
      </h2>
      
      <p className="text-center text-slate-400 mb-6">
        请根据两位辩手的表现进行评分，并选择您支持的一方
      </p>
      
      {/* 评分维度 */}
      {renderScoreSlider(logicScores, setLogicScores, '逻辑严密性', Brain)}
      {renderScoreSlider(persuasionScores, setPersuasionScores, '说服力', Heart)}
      {renderScoreSlider(humorScores, setHumorScores, '幽默感', Laugh)}
      
      {/* 选择支持的辩手 */}
      <div className="mb-6">
        <div className="font-medium text-slate-200 mb-3">选择您支持的辩手</div>
        <div className="grid grid-cols-2 gap-4">
          {participants.map(participant => {
            const isAffirmative = participant.side === 'affirmative';
            const isSelected = preferredModel === participant.model_id;
            
            return (
              <button
                key={participant.model_id}
                onClick={() => setPreferredModel(participant.model_id)}
                className={`p-4 rounded-xl border-2 transition-all ${
                  isSelected
                    ? isAffirmative
                      ? 'border-green-500 bg-green-500/10'
                      : 'border-red-500 bg-red-500/10'
                    : 'border-slate-600 bg-slate-700/30 hover:border-slate-500'
                }`}
              >
                <div className="flex items-center justify-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    isAffirmative ? 'bg-green-600/30' : 'bg-red-600/30'
                  }`}>
                    <span className={`text-lg font-bold ${
                      isAffirmative ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {isAffirmative ? '正' : '反'}
                    </span>
                  </div>
                  <div className="text-left">
                    <div className="font-medium text-slate-200">{participant.display_name}</div>
                    <div className="text-xs text-slate-500">
                      {isAffirmative ? '正方' : '反方'}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
      
      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}
      
      {/* 提交按钮 */}
      <button
        onClick={handleSubmitVote}
        disabled={voting}
        className={`w-full py-3 rounded-xl font-medium transition-all flex items-center justify-center gap-2 ${
          voting
            ? 'bg-slate-600 cursor-not-allowed'
            : 'bg-primary-600 hover:bg-primary-500 text-white'
        }`}
      >
        {voting ? (
          <>
            <div className="loading-spinner w-5 h-5 border-slate-400 border-t-primary-500" />
            <span>提交中...</span>
          </>
        ) : (
          <>
            <ThumbsUp className="w-5 h-5" />
            <span>提交投票</span>
          </>
        )}
      </button>
    </div>
  );
};

export default VotingPanel;
