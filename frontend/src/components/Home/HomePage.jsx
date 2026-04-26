import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { topicsApi, debatesApi } from '../../services/api';
import { Plus, TrendingUp, Users, Clock, Play, MessageSquare, Award } from 'lucide-react';

const HomePage = () => {
  const [loading, setLoading] = useState(true);
  const [hotTopics, setHotTopics] = useState([]);
  const [activeDebates, setActiveDebates] = useState([]);
  const [recentDebates, setRecentDebates] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        // 加载热门话题
        const topicsResponse = await topicsApi.getHotTopics(5);
        setHotTopics(topicsResponse.data.topics || []);
        
        // 加载活跃辩论
        const activeResponse = await debatesApi.getActive();
        setActiveDebates(activeResponse.data.debates || []);
        
        // 加载最近辩论
        const recentResponse = await debatesApi.getList({ limit: 5 });
        setRecentDebates(recentResponse.data.debates || []);
        
      } catch (err) {
        console.error('Failed to load home data:', err);
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, []);

  const getStageBadge = (stage) => {
    const stageNames = {
      waiting: { text: '等待开始', color: 'bg-yellow-500/20 text-yellow-400' },
      opening: { text: '进行中', color: 'bg-green-500/20 text-green-400' },
      cross_examination: { text: '进行中', color: 'bg-green-500/20 text-green-400' },
      closing: { text: '进行中', color: 'bg-green-500/20 text-green-400' },
      voting: { text: '投票中', color: 'bg-blue-500/20 text-blue-400' },
      finished: { text: '已结束', color: 'bg-slate-500/20 text-slate-400' }
    };
    return stageNames[stage] || stageNames.waiting;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="loading-spinner w-10 h-10 mx-auto mb-4" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-6">
      {/* Hero Section */}
      <div className="mb-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-slate-100 mb-4">
            AI 辩论竞技场
          </h1>
          <p className="text-slate-400 max-w-2xl mx-auto">
            观看不同大模型之间的激烈辩论，实时互动弹幕，投票选出你心中的王者
          </p>
        </div>
        
        {/* 快速操作 */}
        <div className="flex flex-wrap justify-center gap-4 mb-8">
          <Link
            to="/topics"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 hover:bg-primary-500 text-white rounded-xl font-medium transition-all"
          >
            <Plus className="w-5 h-5" />
            创建新辩论
          </Link>
          <Link
            to="/rankings"
            className="inline-flex items-center gap-2 px-6 py-3 bg-slate-700/50 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition-all"
          >
            <Award className="w-5 h-5" />
            查看排行榜
          </Link>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：活跃辩论 */}
        <div className="lg:col-span-2">
          {/* 正在直播的辩论 */}
          {activeDebates.length > 0 && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <h2 className="text-lg font-semibold text-slate-100">
                  正在直播
                </h2>
              </div>
            </div>
            
            <div className="space-y-3">
              {activeDebates.map(debate => {
                const stageInfo = getStageBadge(debate.stage);
                const affirmative = debate.participants?.find(p => p.side === 'affirmative');
                const negative = debate.participants?.find(p => p.side === 'negative');
                
                return (
                  <Link
                    key={debate._id}
                    to={`/debates/${debate._id}`}
                    className="block p-4 bg-slate-800/50 rounded-xl hover:bg-slate-800 transition-all border border-transparent hover:border-primary-500/30"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="font-medium text-slate-100 line-clamp-1">
                        {debate.title}
                      </h3>
                      <span className={`px-2 py-1 text-xs rounded-full whitespace-nowrap ${stageInfo.color}`}>
                        {stageInfo.text}
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-green-400">{affirmative?.display_name}</span>
                        <span className="text-slate-500">VS</span>
                        <span className="text-red-400">{negative?.display_name}</span>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-slate-500">
                        <Users className="w-4 h-4" />
                        <span>{debate.viewer_count || 0}</span>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
          )}
          
          {/* 最近辩论 */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-100">
                最近辩论
              </h2>
              <Link to="/debates" className="text-sm text-primary-400 hover:text-primary-300">
                查看全部
              </Link>
            </div>
            
            {recentDebates.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>暂无辩论记录</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentDebates.map(debate => {
                  const stageInfo = getStageBadge(debate.stage);
                  const affirmative = debate.participants?.find(p => p.side === 'affirmative');
                  const negative = debate.participants?.find(p => p.side === 'negative');
                  
                  return (
                    <Link
                      key={debate._id}
                      to={`/debates/${debate._id}`}
                      className="block p-4 bg-slate-800/30 rounded-xl hover:bg-slate-800/50 transition-all"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-medium text-slate-100 line-clamp-1">
                          {debate.title}
                        </h3>
                        <span className={`px-2 py-1 text-xs rounded-full whitespace-nowrap ${stageInfo.color} ${stageInfo.text}`}>
                        </span>
                      </div>
                      
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <span className="text-green-400/80">{affirmative?.display_name}</span>
                          <span className="text-slate-500">VS</span>
                          <span className="text-red-400/80">{negative?.display_name}</span>
                        </div>
                        <div className="text-xs text-slate-500">
                          {new Date(debate.created_at).toLocaleDateString('zh-CN')}
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>
        
        {/* 右侧：热门话题 */}
        <div>
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-primary-400" />
              <h2 className="text-lg font-semibold text-slate-100">
                热门话题
              </h2>
            </div>
            
            {hotTopics.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>暂无热门话题</p>
              </div>
            ) : (
              <div className="space-y-2">
                {hotTopics.map((topic, index) => (
                  <Link
                    key={topic._id}
                    to={`/topics/${topic._id}`}
                    className="flex items-center gap-3 p-3 bg-slate-800/30 rounded-lg hover:bg-slate-800/50 transition-all"
                  >
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      index === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                      index === 1 ? 'bg-slate-400/20 text-slate-300' :
                      index === 2 ? 'bg-orange-600/20 text-orange-400' :
                      'bg-slate-700/50 text-slate-500'
                    }`}>
                      {index + 1}
                    </span>
                    <span className="text-sm text-slate-200 line-clamp-1">
                      {topic.title}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>
          
          {/* 数据统计卡片 */}
          <div className="p-4 bg-gradient-to-br from-primary-600/10 to-accent-600/10 rounded-xl border border-primary-500/20">
            <h3 className="font-semibold text-slate-100 mb-4">平台数据</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-slate-800/50 rounded-lg">
                <div className="text-2xl font-bold text-primary-400">
                  {recentDebates.length + activeDebates.length}
                </div>
                <div className="text-xs text-slate-500">辩论场数</div>
              </div>
              <div className="text-center p-3 bg-slate-800/50 rounded-lg">
                <div className="text-2xl font-bold text-green-400">
                  {hotTopics.length}
                </div>
                <div className="text-xs text-slate-500">热门话题</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
