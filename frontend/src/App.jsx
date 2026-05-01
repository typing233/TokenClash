import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import HomePage from './components/Home/HomePage';
import DebateLive from './components/Debate/DebateLive';
import RankingList from './components/Ranking/RankingList';
import TopicsPage from './components/Topics/TopicsPage';
import CreateTopicPage from './components/Topics/CreateTopicPage';
import ArenaPage from './pages/ArenaPage';
import ArenaLive from './components/Arena/ArenaLive';
import NetworkPage from './pages/NetworkPage';
import LLMConfigPanel from './components/Settings/LLMConfigPanel';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="debates" element={<DebatesPage />} />
          <Route path="arena" element={<ArenaPage />} />
          <Route path="network" element={<NetworkPage />} />
          <Route path="topics" element={<TopicsPage />} />
          <Route path="topics/new" element={<CreateTopicPage />} />
          <Route path="rankings" element={<RankingList />} />
          <Route path="models" element={<LLMConfigPanel />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
        
        <Route path="/debates/:debateId" element={<DebateLive />} />
        <Route path="/arena/:roomId" element={<ArenaLive />} />
      </Routes>
    </Router>
  );
}

function DebatesPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-slate-100 mb-6">辩论列表</h1>
      <p className="text-slate-400">辩论列表页面开发中...</p>
    </div>
  );
}

export default App;
