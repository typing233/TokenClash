import { Outlet, useLocation } from 'react-router-dom';
import Navbar from './Navbar';

const Layout = () => {
  const location = useLocation();
  
  // 检查是否是辩论直播页面
  const isDebateLivePage = location.pathname.startsWith('/debates/') && 
    location.pathname !== '/debates' && 
    location.pathname !== '/debates/';

  // 辩论直播页面不使用布局（全屏模式）
  if (isDebateLivePage) {
    return <Outlet />;
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <Navbar />
      
      {/* 主内容区 */}
      <main className="md:ml-64 pb-16 md:pb-0">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
