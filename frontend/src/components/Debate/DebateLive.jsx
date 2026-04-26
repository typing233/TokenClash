import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDebateStore } from '../../store';
import socketService from '../../services/socket';
import { debatesApi } from '../../services/api';
import DanmakuContainer from '../Danmaku/DanmakuContainer';
import DanmakuInput from '../Danmaku/DanmakuInput';
import { Users, Clock, ChevronLeft, Play, Pause, AlertCircle } from 'lucide-react';

const STAGE_NAMES = {
  waiting: '等待开始',
  opening: '开篇陈词',
  cross_examination: '交叉反驳',
  closing: '总结陈词',
  voting: '投票阶段',
  finished: '辩论结束'
};

const DebateLive = () => {
  const { debateId } = useParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [debate, setDebate] = useState(null);
  const [messages, setMessages] = useState([]);
  const [viewerCount, setViewerCount] = useState(0);
  
  const {
    stage,
    currentRound,
    currentSpeaker,
    setCurrentDebate,
    setMessages: setStoreMessages,
    setStage,
    setCurrentRound,
    setCurrentSpeaker,
    setViewerCount: setStoreViewerCount,
    setIsJoined,
    addMessage,
    clearDebate
  } = useDebateStore(state => ({
    stage: state.stage,
    currentRound: state.currentRound,
    currentSpeaker: state.currentSpeaker,
    setCurrentDebate: state.setCurrentDebate,
    setMessages: state.setMessages,
    setStage: state.setStage,
    setCurrentRound: state.setCurrentRound,
    setCurrentSpeaker: state.setCurrentSpeaker,
    setViewerCount: state.setViewerCount,
    setIsJoined: state.setIsJoined,
    addMessage: state.addMessage,
    clearDebate: state.clearDebate
  }));

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 加载辩论数据
  useEffect(() => {
    const loadDebate = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // 连接Socket.IO
        socketService.connect();
        
        // 获取辩论详情
        const response = await debatesApi.getById(debateId);
        const debateData = response.data;
        
        setDebate(debateData);
        setCurrentDebate(debateData);
        setStage(debateData.stage);
        setCurrentRound(debateData.current_round);
        setCurrentSpeaker(debateData.current_speaker);
        setViewerCount(debateData.viewer_count);
        
        // 获取消息历史
        const messagesResponse = await debatesApi.getMessages(debateId, { limit: 100 });
        const messagesData = messagesResponse.data.messages || [];
        setMessages(messagesData);
        setStoreMessages(messagesData);
        
        // 加入辩论房间
        socketService.joinDebate(debateId);
        setIsJoined(true);
        
      } catch (err) {
        console.error('Failed to load debate:', err);
        setError(err.response?.data?.detail || '加载辩论失败');
      } finally {
        setLoading(false);
      }
    };
    
    loadDebate();
    
    return () => {
      // 离开辩论房间
      socketService.leaveDebate(debateId);
      setIsJoined(false);
      clearDebate();
    };
  }, [debateId]);

  // 监听Socket.IO事件
  useEffect(() => {
    const unsubscribers = [];
    
    // 新消息
    const handleNewMessage = (message) => {
      setMessages(prev => [...prev, message]);
      addMessage(message);
      
      // 更新状态
      if (message.event_type === 'stage_change') {
        setStage(message.metadata?.stage);
      }
    };
    unsubscribers.push(socketService.on('new_message', handleNewMessage));
    
    // 辩论状态更新
    const handleStateUpdate = (update) => {
      if (update.stage) setStage(update.stage);
      if (update.current_round !== undefined) setCurrentRound(update.current_round);
      if (update.current_speaker) setCurrentSpeaker(update.current_speaker);
    };
    unsubscribers.push(socketService.on('debate_state_update', handleStateUpdate));
    
    // 用户加入/离开
    const handleUserJoined = (data) => {
      setViewerCount(prev => prev + 1);
      setStoreViewerCount(prev => prev + 1);
    };
    unsubscribers.push(socketService.on('user_joined', handleUserJoined));
    
    const handleUserLeft = (data) => {
      setViewerCount(prev => Math.max(0, prev - 1));
      setStoreViewerCount(prev => Math.max(0, prev - 1));
    };
    unsubscribers.push(socketService.on('user_left', handleUserLeft));
    
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
    };
  }, [addMessage, setStage, setCurrentRound, setCurrentSpeaker, setStoreViewerCount]);

  const getParticipantByModelId = (modelId) => {
    if (!debate?.participants) return null;
    return debate.participants.find(p => p.model_id === modelId);
  };

  const renderMessage = (message, index) => {
    const messageType = message.message_type;
    
    if (messageType === 'system') {
      return (
        <div key={index} className="flex justify-center my-4">
          <div className="px-4 py-2 bg-slate-700/80 rounded-full text-sm text-slate-200">
            {message.content}
          </div>
        </div>
      );
    }
    
    if (messageType === 'model') {
      const isAffirmative = message.side === 'affirmative';
      const participant = getParticipantByModelId(message.model_id);
      const isSpeaking = currentSpeaker === message.model_id;
      
      return (
        <div key={index} className={`flex mb-4 ${isAffirmative ? 'justify-end' : 'justify-start'}`}>
          <div className={`max-w-[70%] ${isAffirmative ? 'order-2' : 'order-1'}`}>
            {/* 模型名称和状态 */}
            <div className={`flex items-center gap-2 mb-1 ${isAffirmative ? 'justify-end' : 'justify-start'}`}>
              <span className={`text-sm font-medium ${
                isAffirmative ? 'text-green-400' : 'text-red-400'
              }`}>
                {participant?.display_name || message.display_name}
              </span>
              {isSpeaking && (
                <div className="speaking-indicator">
                  <div className="speaking-dot" />
                  <div className="speaking-dot" />
                  <div className="speaking-dot" />
                </div>
              )}
            </div>
            
            {/* 消息气泡 */}
            <div className={`px-4 py-3 rounded-2xl ${
              isAffirmative 
                ? 'bg-gradient-to-br from-green-600 to-green-700 rounded-tr-none' 
                : 'bg-gradient-to-br from-red-600 to-red-700 rounded-tl-none'
            }`}>
              <p className="text-white whitespace-pre-wrap leading-relaxed">
                {message.content}
              </p>
            </div>
            
            {/* 时间戳 */}
            <div className={`text-xs text-slate-500 mt-1 ${isAffirmative ? 'text-right' : 'text-left'}`}>
              {new Date(message.created_at).toLocaleTimeString('zh-CN')}
            </div>
          </div>
          
          {/* 头像/图标 */}
          <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
            isAffirmative 
              ? 'bg-green-600/20 ml-3 order-1' 
              : 'bg-red-600/20 mr-3 order-2'
          }`}>
            <span className={`text-lg font-bold ${
              isAffirmative ? 'text-green-400' : 'text-red-400'
            }`}>
              {isAffirmative ? '正' : '反'}
            </span>
          </div>
        </div>
      );
    }
    
    return null;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="loading-spinner w-12 h-12 mx-auto mb-4" />
          <p className="text-slate-400">加载辩论中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen">
        <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
        <p className="text-slate-300 mb-4">{error}</p>
        <button
          onClick={() => navigate('/')}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition-colors"
        >
          返回首页
        </button>
      </div>
    );
  }

  const affirmative = debate?.participants?.find(p => p.side === 'affirmative');
  const negative = debate?.participants?.find(p => p.side === 'negative');

  return (
    <div className="h-screen flex flex-col bg-slate-900">
      {/* 顶部信息栏 */}
      <div className="bg-slate-800/90 backdrop-blur-sm border-b border-slate-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            
            <div>
              <h1 className="text-lg font-semibold text-slate-100">{debate?.title}</h1>
              <div className="flex items-center gap-3 text-sm text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {STAGE_NAMES[stage] || stage}
                </span>
                {currentRound > 0 && (
                  <span>第 {currentRound} 轮</span>
                )}
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* 观众数 */}
            <div className="flex items-center gap-2 text-slate-400">
              <Users className="w-5 h-5" />
              <span>{viewerCount}</span>
            </div>
          </div>
        </div>
        
        {/* 正反方信息 */}
        <div className="flex items-center justify-between mt-3 px-2">
          {/* 正方 */}
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
            currentSpeaker === affirmative?.model_id ? 'bg-green-600/20' : ''
          }`}>
            <div className="w-8 h-8 rounded-full bg-green-600/30 flex items-center justify-center">
              <span className="text-green-400 text-sm font-bold">正</span>
            </div>
            <div>
              <p className="text-sm font-medium text-green-400">{affirmative?.display_name}</p>
              <p className="text-xs text-slate-500">正方</p>
            </div>
          </div>
          
          {/* VS */}
          <div className="text-xl font-bold text-slate-500">VS</div>
          
          {/* 反方 */}
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
            currentSpeaker === negative?.model_id ? 'bg-red-600/20' : ''
          }`}>
            <div>
              <p className="text-sm font-medium text-red-400 text-right">{negative?.display_name}</p>
              <p className="text-xs text-slate-500 text-right">反方</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-red-600/30 flex items-center justify-center">
              <span className="text-red-400 text-sm font-bold">反</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 消息列表区 */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-500">
              <Play className="w-16 h-16 mb-4 opacity-50" />
              <p>辩论即将开始...</p>
            </div>
          ) : (
            <>
              {messages.map(renderMessage)}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
        
        {/* 弹幕层 (覆盖在消息层之上) */}
        <div className="absolute inset-0 pointer-events-none" style={{ top: '120px', bottom: '60px' }}>
          <DanmakuContainer>
            {/* 弹幕层没有额外内容 */}
          </DanmakuContainer>
        </div>
      </div>
      
      {/* 底部弹幕输入区 */}
      <DanmakuInput debateId={debateId} />
    </div>
  );
};

export default DebateLive;
