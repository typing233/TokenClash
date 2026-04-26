import { useState, useRef, useEffect } from 'react';
import { Send, Smile, Palette } from 'lucide-react';
import socketService from '../../services/socket';
import { useUserStore } from '../../store';

const COLORS = [
  '#ffffff', '#ff0000', '#00ff00', '#0000ff',
  '#ffff00', '#ff00ff', '#00ffff',
  '#ff8c00', '#9370db', '#00ced1'
];

const DanmakuInput = ({ debateId }) => {
  const [content, setContent] = useState('');
  const [selectedColor, setSelectedColor] = useState('#ffffff');
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const inputRef = useRef(null);
  const colorPickerRef = useRef(null);
  
  const user = useUserStore(state => state.user);
  
  // 点击外部关闭颜色选择器
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (colorPickerRef.current && !colorPickerRef.current.contains(event.target)) {
        setShowColorPicker(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  const handleSend = async () => {
    if (!content.trim() || isSending) return;
    
    setIsSending(true);
    
    try {
      const danmakuData = {
        debate_id: debateId,
        content: content.trim(),
        user_id: user?._id || null,
        user_name: user?.display_name || user?.username || '匿名用户',
        color: selectedColor,
        position: 'top',
      };
      
      // 发送弹幕
      socketService.sendDanmaku(danmakuData);
      
      // 清空输入
      setContent('');
      
    } catch (error) {
      console.error('Failed to send danmaku:', error);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  return (
    <div className="flex items-center gap-2 p-3 bg-slate-800/90 backdrop-blur-sm border-t border-slate-700">
      {/* 颜色选择器 */}
      <div className="relative" ref={colorPickerRef}>
        <button
          onClick={() => setShowColorPicker(!showColorPicker)}
          className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          title="选择颜色"
        >
          <Palette className="w-5 h-5" style={{ color: selectedColor }} />
        </button>
        
        {showColorPicker && (
          <div className="absolute bottom-full left-0 mb-2 p-2 bg-slate-700 rounded-lg shadow-xl border border-slate-600">
            <div className="grid grid-cols-5 gap-1">
              {COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => {
                    setSelectedColor(color);
                    setShowColorPicker(false);
                  }}
                  className={`w-6 h-6 rounded-full border-2 transition-transform hover:scale-110 ${
                    selectedColor === color ? 'border-white' : 'border-transparent'
                  }`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </div>
        )}
      </div>
      
      {/* 表情按钮（预留） */}
      <button
        className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-slate-200"
        title="表情"
      >
        <Smile className="w-5 h-5" />
      </button>
      
      {/* 输入框 */}
      <div className="flex-1 relative">
        <input
          ref={inputRef}
          type="text"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="发送弹幕互动..."
          maxLength={100}
          className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 placeholder-slate-400 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-colors"
          style={{ color: selectedColor }}
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">
          {content.length}/100
        </span>
      </div>
      
      {/* 发送按钮 */}
      <button
        onClick={handleSend}
        disabled={!content.trim() || isSending}
        className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
          content.trim() && !isSending
            ? 'bg-primary-600 hover:bg-primary-500 text-white'
            : 'bg-slate-700 text-slate-500 cursor-not-allowed'
        }`}
      >
        {isSending ? (
          <div className="loading-spinner w-4 h-4" />
        ) : (
          <Send className="w-4 h-4" />
        )}
        <span className="hidden sm:inline">发送</span>
      </button>
    </div>
  );
};

export default DanmakuInput;
