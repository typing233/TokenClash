import { useState, useEffect, useRef, useCallback } from 'react';
import { useDebateStore } from '../../store';
import socketService from '../../services/socket';

// 弹幕轨道数量
const TRACK_COUNT = 8;
// 每条轨道高度
const TRACK_HEIGHT = 36;
// 弹幕显示时间（毫秒）
const DURATION = 10000;

const DanmakuContainer = ({ children }) => {
  const containerRef = useRef(null);
  const [danmakus, setDanmakus] = useState([]);
  const [tracks, setTracks] = useState(Array(TRACK_COUNT).fill(null));
  const addDanmaku = useDebateStore(state => state.addDanmaku);
  
  // 生成随机颜色
  const getRandomColor = () => {
    const colors = [
      '#ffffff', '#ff0000', '#00ff00', '#0000ff',
      '#ffff00', '#ff00ff', '#00ffff',
      '#ff8c00', '#9370db', '#00ced1'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  };
  
  // 找到可用的轨道
  const findAvailableTrack = useCallback(() => {
    const now = Date.now();
    for (let i = 0; i < TRACK_COUNT; i++) {
      if (!tracks[i] || now - tracks[i] > 2000) {
        return i;
      }
    }
    return Math.floor(Math.random() * TRACK_COUNT);
  }, [tracks]);
  
  // 添加新弹幕
  const handleNewDanmaku = useCallback((danmaku) => {
    const trackIndex = findAvailableTrack();
    const now = Date.now();
    
    const newDanmaku = {
      ...danmaku,
      id: danmaku._id || `danmaku_${now}_${Math.random()}`,
      track: trackIndex,
      createdAt: now,
      color: danmaku.color || getRandomColor(),
    };
    
    setDanmakus(prev => [...prev.slice(-100), newDanmaku);
    addDanmaku(newDanmaku);
    
    // 更新轨道状态
    setTracks(prev => {
      const newTracks = [...prev];
      newTracks[trackIndex] = now;
      return newTracks;
    });
  }, [findAvailableTrack, addDanmaku]);
  
  // 清理过期弹幕
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      setDanmakus(prev => prev.filter(d => now - d.createdAt < DURATION + 2000));
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);
  
  // 监听Socket.IO弹幕事件
  useEffect(() => {
    const unsubscribe = socketService.on('new_danmaku', handleNewDanmaku);
    
    return () => unsubscribe();
  }, [handleNewDanmaku]);
  
  return (
    <div ref={containerRef} className="danmaku-container relative w-full h-full overflow-hidden">
      {/* 渲染弹幕 */}
      {danmakus.map((danmaku) => (
        <DanmakuItem 
          key={danmaku.id} 
          danmaku={danmaku}
          containerHeight={containerRef.current?.offsetHeight || 400}
        />
      ))}
      
      {/* 子元素（如弹幕输入框等） */}
      {children}
    </div>
  );
};

const DanmakuItem = ({ danmaku, containerHeight }) => {
  const [position, setPosition] = useState({ top: 0, left: '100%' });
  const [isAnimating, setIsAnimating] = useState(true);
  
  useEffect(() => {
    // 计算垂直位置
    const trackTop = danmaku.track * TRACK_HEIGHT;
    // 确保在容器内垂直居中分布
    const availableSpace = containerHeight - (TRACK_COUNT * TRACK_HEIGHT);
    const offset = availableSpace > 0 ? availableSpace / 2 : 0;
    const top = offset + trackTop;
    
    setPosition({ top, left: '100%' });
    setIsAnimating(true);
    
    // 动画结束后移除
    const timer = setTimeout(() => {
      setIsAnimating(false);
    }, DURATION);
    
    return () => clearTimeout(timer);
  }, [danmaku.id, danmaku.track, containerHeight]);
  
  if (!isAnimating) return null;
  
  return (
    <div
      className="danmaku-item absolute whitespace-nowrap pointer-events-auto cursor-default"
      style={{
        top: `${position.top}px`,
        left: position.left,
        color: danmaku.color,
        textShadow: '1px 1px 2px rgba(0,0,0,0.8), -1px -1px 2px rgba(0,0,0,0.8)',
        fontSize: '22px',
        fontWeight: 'bold',
        animation: `danmaku-scroll ${DURATION / 1000}s linear forwards`,
        zIndex: 10,
      }}
    >
      {danmaku.user_name && (
        <span className="opacity-80 mr-1">[{danmaku.user_name}]</span>
      )}
      {danmaku.content}
    </div>
  );
};

export default DanmakuContainer;
