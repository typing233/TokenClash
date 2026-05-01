export default function EnergyBar({ current, max = 100, color = 'green', label = '' }) {
  const percentage = Math.min(100, Math.max(0, (current / max) * 100));
  
  const colorClasses = {
    green: {
      bg: 'bg-green-600/20',
      fill: 'bg-green-500',
      glow: 'shadow-[0_0_10px_rgba(34,197,94,0.5)]',
      text: 'text-green-400'
    },
    red: {
      bg: 'bg-red-600/20',
      fill: 'bg-red-500',
      glow: 'shadow-[0_0_10px_rgba(239,68,68,0.5)]',
      text: 'text-red-400'
    },
    blue: {
      bg: 'bg-blue-600/20',
      fill: 'bg-blue-500',
      glow: 'shadow-[0_0_10px_rgba(59,130,246,0.5)]',
      text: 'text-blue-400'
    }
  };
  
  const colors = colorClasses[color] || colorClasses.green;
  
  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between text-xs mb-1">
          <span className="text-slate-400">{label}</span>
          <span className={colors.text}>
            {current} / {max}
          </span>
        </div>
      )}
      
      <div className={`w-full h-3 rounded-full overflow-hidden ${colors.bg}`}>
        <div 
          className={`h-full rounded-full transition-all duration-300 ease-out ${colors.fill} ${percentage > 20 ? colors.glow : ''}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      
      {!label && (
        <div className="flex justify-end text-xs mt-1">
          <span className={colors.text}>
            {current} / {max}
          </span>
        </div>
      )}
    </div>
  );
}
