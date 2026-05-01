import { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';

export default function ArenaCountdown({ current, total = 60 }) {
  const [animatedValue, setAnimatedValue] = useState(current);
  const percentage = (current / total) * 100;
  
  useEffect(() => {
    setAnimatedValue(current);
  }, [current]);
  
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  const isLow = percentage <= 20;
  const isMedium = percentage <= 50;
  
  return (
    <div className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700 py-3">
      <div className="max-w-2xl mx-auto px-4">
        <div className="flex items-center justify-center gap-3">
          <Clock className={`w-5 h-5 ${
            isLow ? 'text-red-400 animate-pulse' : isMedium ? 'text-yellow-400' : 'text-primary-400'
          }`} />
          
          <div className="flex-1 max-w-md">
            <div className="flex justify-between text-xs mb-1">
              <span className={`font-mono text-lg font-bold ${
                isLow ? 'text-red-400' : isMedium ? 'text-yellow-400' : 'text-slate-200'
              }`}>
                {formatTime(current)}
              </span>
              <span className="text-slate-500">
                剩余时间
              </span>
            </div>
            
            <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-1000 ease-linear ${
                  isLow 
                    ? 'bg-red-500 animate-pulse' 
                    : isMedium 
                      ? 'bg-yellow-500' 
                      : 'bg-primary-500'
                }`}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
