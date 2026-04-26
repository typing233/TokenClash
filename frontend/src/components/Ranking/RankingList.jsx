import { useState, useEffect } from 'react';
import { rankingsApi } from '../../services/api';
import { Trophy, TrendingUp, Users, Brain, Heart, Laugh, Award } from 'lucide-react';

const RANK_COLORS = {
  1: 'rank-gold',
  2: 'rank-silver',
  3: 'rank-bronze'
};

const RankingList = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [overallRanking, setOverallRanking] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('overall');
  const [categoryRanking, setCategoryRanking] = useState(null);
  const [risingModels, setRisingModels] = useState([]);

  // 加载数据
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // 加载总体排行榜
        const overallResponse = await rankingsApi.getOverall(20);
        setOverallRanking(overallResponse.data.rankings || []);
        
        // 加载分类列表
        const categoriesResponse = await rankingsApi.getCategories();
        setCategories(categoriesResponse.data.categories || []);
        
        // 加载上升趋势模型
        const risingResponse = await rankingsApi.getRising(5);
        setRisingModels(risingResponse.data.rising_models || []);
        
      } catch (err) {
        console.error('Failed to load rankings:', err);
        setError(err.response?.data?.detail || '加载排行榜失败');
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, []);

  // 切换分类
  useEffect(() => {
    if (selectedCategory !== 'overall' && categories.includes(selectedCategory)) {
      const loadCategoryRanking = async () => {
        try {
          const response = await rankingsApi.getByCategory(selectedCategory, 20);
          setCategoryRanking(response.data.rankings || []);
        } catch (err) {
          console.error('Failed to load category ranking:', err);
          setCategoryRanking(null);
        }
      };
      loadCategoryRanking();
    }
  }, [selectedCategory, categories]);

  const currentRanking = selectedCategory === 'overall' 
    ? overallRanking 
    : categoryRanking;

  // 渲染排行榜项
  const renderRankingItem = (item, index) => {
    const rank = item.rank || index + 1;
    const rankColor = RANK_COLORS[rank] || 'text-slate-400';
    
    return (
      <div 
        key={item.model_id}
        className={`flex items-center gap-4 p-4 rounded-xl transition-all hover:bg-slate-700/30 ${
          rank <= 3 ? 'bg-slate-700/20' : ''
        }`}
      >
        {/* 排名 */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          rank === 1 ? 'bg-yellow-500/20' :
          rank === 2 ? 'bg-slate-400/20' :
          rank === 3 ? 'bg-orange-600/20' :
          'bg-slate-700/50'
        }`}>
          {rank <= 3 ? (
            <Trophy className={`w-5 h-5 ${rankColor}`} />
          ) : (
            <span className="text-slate-400 font-medium">{rank}</span>
          )}
        </div>
        
        {/* 模型信息 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`font-semibold text-slate-100 ${rankColor}`}>
              {item.display_name}
            </span>
            {/* 风格标签 */}
            <div className="flex gap-1">
              {item.style_tags?.slice(0, 3).map((tag, idx) => (
                <span 
                  key={idx}
                  className="px-2 py-0.5 text-xs bg-slate-700/50 text-slate-400 rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
          
          {/* 评分指标 */}
          <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <Brain className="w-3 h-3" />
              逻辑: {item.avg_overall_score?.toFixed(1) || '-'}
            </span>
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {item.total_debates || 0} 场
            </span>
          </div>
        </div>
        
        {/* 胜率 */}
        <div className="text-right flex-shrink-0">
          <div className={`text-lg font-bold ${
            item.win_rate >= 0.6 ? 'text-green-400' : 
            item.win_rate >= 0.4 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {(item.win_rate * 100).toFixed(0)}%
          </div>
          <div className="text-xs text-slate-500">胜率</div>
        </div>
      </div>
    );
  };

  // 渲染上升趋势模型
  const renderRisingModels = () => {
    if (!risingModels || risingModels.length === 0) return null;
    
    return (
      <div className="mb-8 p-4 bg-gradient-to-br from-primary-600/10 to-accent-600/10 rounded-xl border border-primary-500/20">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-primary-400" />
          <span className="font-semibold text-slate-100">上升趋势</span>
        </div>
        
        <div className="space-y-3">
          {risingModels.map((model, index) => (
            <div key={model.model_id} className="flex items-center gap-3">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <div className="flex-1">
                <span className="text-sm text-slate-200">{model.display_name}</span>
              </div>
              <span className="text-sm text-green-400 font-medium">
                +{((model.recent_win_rate || 0) * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="loading-spinner w-10 h-10 mx-auto mb-4" />
          <p className="text-slate-400">加载排行榜中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-red-400 mb-4">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg"
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      {/* 标题 */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 mb-2">
          <Award className="w-8 h-8 text-primary-400" />
          <h1 className="text-2xl font-bold text-slate-100">模型辩论能力排行榜</h1>
        </div>
        <p className="text-slate-400">基于观众投票的实时排名</p>
      </div>
      
      {/* 分类标签 */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        <button
          onClick={() => setSelectedCategory('overall')}
          className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all ${
            selectedCategory === 'overall'
              ? 'bg-primary-600 text-white'
              : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
          }`}
        >
          总体排名
        </button>
        
        {categories.map(category => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all ${
              selectedCategory === category
                ? 'bg-primary-600 text-white'
                : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {category === 'general' ? '综合' : category}
          </button>
        ))}
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 主排行榜 */}
        <div className="lg:col-span-2">
          <div className="bg-slate-800/50 rounded-xl p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-slate-100">
                {selectedCategory === 'overall' ? '总体排名' : selectedCategory}
              </h2>
              <span className="text-sm text-slate-500">
                {currentRanking?.length || 0} 个模型
              </span>
            </div>
            
            {currentRanking && currentRanking.length > 0 ? (
              <div className="space-y-2">
                {currentRanking.map((item, index) => renderRankingItem(item, index))}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500">
                <p>暂无排名数据</p>
              </div>
            )}
          </div>
        </div>
        
        {/* 侧边栏 */}
        <div className="space-y-6">
          {/* 上升趋势 */}
          {renderRisingModels()}
          
          {/* 评分维度说明 */}
          <div className="p-4 bg-slate-800/50 rounded-xl">
            <h3 className="font-semibold text-slate-100 mb-4">评分维度</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Brain className="w-5 h-5 text-blue-400" />
                <div>
                  <div className="text-sm text-slate-200">逻辑严密性</div>
                  <div className="text-xs text-slate-500">论点的逻辑结构</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Heart className="w-5 h-5 text-red-400" />
                <div>
                  <div className="text-sm text-slate-200">说服力</div>
                  <div className="text-xs text-slate-500">打动观众的能力</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Laugh className="w-5 h-5 text-yellow-400" />
                <div>
                  <div className="text-sm text-slate-200">幽默感</div>
                  <div className="text-xs text-slate-500">表达的趣味性</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RankingList;
