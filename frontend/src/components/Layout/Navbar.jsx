import { Link, useLocation } from 'react-router-dom';
import { Home, MessageSquare, Award, Plus, Swords, Network, Settings2 } from 'lucide-react';

const Navbar = () => {
  const location = useLocation();
  
  const navItems = [
    { path: '/', label: '首页', icon: Home },
    { path: '/debates', label: '辩论', icon: Swords },
    { path: '/arena', label: '竞技场', icon: Swords },
    { path: '/network', label: '关系网络', icon: Network },
    { path: '/topics', label: '话题', icon: Plus },
    { path: '/rankings', label: '排行', icon: Award },
    { path: '/models', label: '模型配置', icon: Settings2 },
  ];
  
  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 md:top-0 md:bottom-auto bg-slate-900/95 backdrop-blur-sm border-b md:border-b-0 md:border-r border-slate-800 z-50">
      {/* 移动端底部导航 */}
      <div className="md:hidden">
        <div className="flex items-center justify-around py-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center px-4 py-2 rounded-lg transition-all ${
                  active
                    ? 'text-primary-400'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-xs mt-1">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
      
      {/* 桌面端侧边导航 */}
      <div className="hidden md:flex md:flex-col md:w-64 md:h-screen md:fixed md:left-0 md:top-0 md:py-6 md:px-4">
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
            <Swords className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-slate-100">TokenClash</h1>
            <p className="text-xs text-slate-500">AI 辩论竞技场</p>
          </div>
        </div>
        
        {/* 导航项 */}
        <div className="flex-1 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                  active
                    ? 'bg-primary-600/20 text-primary-400 font-medium'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
        
        {/* 底部信息 */}
        <div className="mt-auto pt-4 border-t border-slate-800">
          <div className="px-4 py-3 text-xs text-slate-500">
            <p>火山方舟 AI 辩论</p>
            <p className="mt-1">v1.0.0</p>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
