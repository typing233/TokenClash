export default function SkillCard({ skill, selectedTarget, onUse }) {
  const IconComponent = skill.icon;
  const isDisabled = !selectedTarget;
  
  return (
    <button
      onClick={onUse}
      disabled={isDisabled}
      className={`relative p-3 rounded-xl border transition-all duration-200 group ${
        isDisabled
          ? 'bg-slate-800/30 border-slate-700/50 cursor-not-allowed opacity-60'
          : 'bg-slate-800/50 border-slate-600 hover:border-primary-500 hover:bg-slate-700/50 cursor-pointer hover:scale-105'
      }`}
    >
      <div className="flex flex-col items-center gap-2">
        <div 
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${
            isDisabled 
              ? 'bg-slate-700/50' 
              : 'group-hover:scale-110'
          }`}
          style={{ 
            backgroundColor: isDisabled ? undefined : `${skill.color}20`,
            color: skill.color
          }}
        >
          <IconComponent className="w-5 h-5" />
        </div>
        
        <div className="text-center">
          <p className="text-sm font-medium text-slate-200">{skill.name}</p>
          <p className="text-xs text-slate-500 mt-0.5">{skill.description}</p>
        </div>
        
        <div className="flex items-center gap-1 text-xs text-slate-400">
          <span>消耗: {skill.cost}</span>
        </div>
      </div>
      
      {!isDisabled && (
        <div 
          className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
          style={{ boxShadow: `0 0 20px ${skill.color}40` }}
        />
      )}
    </button>
  );
}
