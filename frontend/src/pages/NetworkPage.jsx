import { useState, useEffect, useCallback } from 'react';
import { networkApi, dnaApi } from '../services/api';
import { useNetworkStore } from '../store';
import { 
  Network, 
  Search, 
  Eye, 
  RefreshCw, 
  Loader2, 
  AlertCircle,
  ChevronRight,
  Users,
  Link2,
  Zap,
  Info
} from 'lucide-react';
import Network3D from '../components/Network/Network3D';

export default function NetworkPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [graphData, setLocalGraphData] = useState(null);
  const [hiddenRelations, setHiddenRelations] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeDetail, setNodeDetail] = useState(null);
  const [showLabels, setShowLabels] = useState(true);
  const [showHiddenRelations, setShowHiddenRelations] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [rebuilding, setRebuilding] = useState(false);
  const [loadingHidden, setLoadingHidden] = useState(false);

  const {
    nodes,
    edges,
    setGraphData: setStoreGraphData,
    addHiddenRelation,
    selectNode
  } = useNetworkStore(state => ({
    nodes: state.nodes,
    edges: state.edges,
    setGraphData: state.setGraphData,
    addHiddenRelation: state.addHiddenRelation,
    selectNode: state.selectNode
  }));

  useEffect(() => {
    loadGraphData();
  }, []);

  const loadGraphData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await networkApi.getGraph();
      const data = response.data;
      
      setLocalGraphData(data);
      setStoreGraphData(data);
      
    } catch (err) {
      console.error('Failed to load graph data:', err);
      setError(err.response?.data?.detail || '加载关系网络失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRebuildGraph = async () => {
    try {
      setRebuilding(true);
      await networkApi.rebuildGraph();
      await loadGraphData();
    } catch (err) {
      console.error('Failed to rebuild graph:', err);
      setError('重建关系网络失败');
    } finally {
      setRebuilding(false);
    }
  };

  const handleLoadHiddenRelations = async () => {
    try {
      setLoadingHidden(true);
      const response = await networkApi.getHiddenRelations();
      const pairs = response.data?.hidden_pairs || [];
      
      setHiddenRelations(pairs);
      pairs.forEach(pair => addHiddenRelation(pair));
      
    } catch (err) {
      console.error('Failed to load hidden relations:', err);
    } finally {
      setLoadingHidden(false);
    }
  };

  const handleSelectNode = useCallback(async (nodeId, neighbors) => {
    setSelectedNode(nodeId);
    selectNode(nodeId);
    
    try {
      const response = await networkApi.getNodeDetail(nodeId);
      setNodeDetail(response.data);
    } catch (err) {
      console.error('Failed to load node detail:', err);
      setNodeDetail({
        id: nodeId,
        neighbors: neighbors || []
      });
    }
  }, [selectNode]);

  const filteredNodes = useCallback(() => {
    if (!searchQuery || !graphData?.nodes) return graphData?.nodes || [];
    return graphData.nodes.filter(node => 
      node.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      node.id?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [graphData, searchQuery]);

  if (loading && !graphData) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-900">
        <div className="text-center">
          <Loader2 className="w-12 h-12 mx-auto mb-4 text-primary-500 animate-spin" />
          <p className="text-slate-400">加载关系网络中...</p>
        </div>
      </div>
    );
  }

  if (error && !graphData) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-slate-900">
        <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
        <p className="text-slate-300 mb-4">{error}</p>
        <button
          onClick={loadGraphData}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition-colors"
        >
          重试
        </button>
      </div>
    );
  }

  const stats = graphData?.stats || {};
  const totalNodes = stats.nodes || 0;
  const totalEdges = stats.edges || 0;
  const avgDegree = stats.avg_degree ? stats.avg_degree.toFixed(2) : 0;

  return (
    <div className="min-h-screen bg-slate-900 flex">
      {/* 左侧边栏 */}
      <div className="w-80 bg-slate-800/50 border-r border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-primary-600/20 rounded-lg">
              <Network className="w-5 h-5 text-primary-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-100">关系网络</h1>
              <p className="text-xs text-slate-500">Token关联可视化</p>
            </div>
          </div>
          
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索Token..."
              className="w-full pl-9 pr-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary-500"
            />
          </div>
        </div>
        
        {/* 统计信息 */}
        <div className="p-4 border-b border-slate-700">
          <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">统计</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-700/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Users className="w-4 h-4 text-primary-400" />
                <span className="text-xs text-slate-500">节点</span>
              </div>
              <p className="text-xl font-semibold text-slate-200">{totalNodes}</p>
            </div>
            <div className="bg-slate-700/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Link2 className="w-4 h-4 text-green-400" />
                <span className="text-xs text-slate-500">边</span>
              </div>
              <p className="text-xl font-semibold text-slate-200">{totalEdges}</p>
            </div>
          </div>
          <div className="mt-3 bg-slate-700/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-4 h-4 text-yellow-400" />
              <span className="text-xs text-slate-500">平均连接度</span>
            </div>
            <p className="text-xl font-semibold text-slate-200">{avgDegree}</p>
          </div>
        </div>
        
        {/* 控制选项 */}
        <div className="p-4 border-b border-slate-700">
          <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">选项</h3>
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showLabels}
                onChange={(e) => setShowLabels(e.target.checked)}
                className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-primary-500 focus:ring-primary-500"
              />
              <span className="text-sm text-slate-300">显示标签</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showHiddenRelations}
                onChange={(e) => setShowHiddenRelations(e.target.checked)}
                className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-primary-500 focus:ring-primary-500"
              />
              <span className="text-sm text-slate-300">显示隐藏关系</span>
            </label>
          </div>
          
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleRebuildGraph}
              disabled={rebuilding}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-300 rounded-lg text-sm transition-colors"
            >
              {rebuilding ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              重建
            </button>
            <button
              onClick={handleLoadHiddenRelations}
              disabled={loadingHidden}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-primary-600/20 hover:bg-primary-600/30 disabled:opacity-50 text-primary-400 rounded-lg text-sm transition-colors"
            >
              {loadingHidden ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
              发现隐藏
            </button>
          </div>
        </div>
        
        {/* 节点详情 */}
        {selectedNode && nodeDetail && (
          <div className="p-4 flex-1 overflow-y-auto">
            <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">
              节点详情
            </h3>
            <div className="bg-slate-700/30 rounded-lg p-3 mb-3">
              <p className="text-sm font-medium text-primary-400 mb-1">
                {nodeDetail.name || nodeDetail.id}
              </p>
              <p className="text-xs text-slate-500">{nodeDetail.id}</p>
              {nodeDetail.degree !== undefined && (
                <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                  <span>连接度: {nodeDetail.degree}</span>
                </div>
              )}
            </div>
            
            {nodeDetail.neighbors?.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-2">
                  关联 Token ({nodeDetail.neighbor_count || nodeDetail.neighbors.length})
                </p>
                <div className="space-y-1">
                  {nodeDetail.neighbors.slice(0, 10).map((neighbor, i) => (
                    <button
                      key={i}
                      onClick={() => handleSelectNode(neighbor.id, [])}
                      className="w-full flex items-center justify-between px-3 py-2 bg-slate-700/20 hover:bg-slate-700/40 rounded-lg text-sm text-slate-300 transition-colors"
                    >
                      <span className="truncate">
                        {neighbor.name || neighbor.id}
                      </span>
                      <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* 隐藏关系列表 */}
        {hiddenRelations.length > 0 && showHiddenRelations && (
          <div className="p-4 border-t border-slate-700">
            <h3 className="text-xs font-medium text-yellow-400/80 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Link2 className="w-4 h-4" />
              隐藏关系 (Adamic-Adar)
            </h3>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {hiddenRelations.slice(0, 5).map((rel, i) => (
                <div
                  key={i}
                  className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-yellow-300/80 truncate">
                      {rel.model1_display_name || rel.model1_id}
                    </span>
                    <Link2 className="w-3 h-3 text-yellow-400 mx-1 flex-shrink-0" />
                    <span className="text-yellow-300/80 truncate">
                      {rel.model2_display_name || rel.model2_id}
                    </span>
                  </div>
                  <div className="text-right mt-1">
                    <span className="text-xs text-yellow-400/60">
                      相似度: {(rel.score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {/* 主内容区 - 3D网络图 */}
      <div className="flex-1 relative">
        {graphData && (
          <Network3D
            graphData={graphData}
            hiddenRelations={showHiddenRelations ? hiddenRelations : []}
            selectedNode={selectedNode}
            onSelectNode={handleSelectNode}
            showLabels={showLabels}
          />
        )}
        
        {/* 操作提示 */}
        <div className="absolute bottom-4 left-4">
          <div className="bg-slate-800/90 backdrop-blur-sm border border-slate-700 rounded-lg p-3 max-w-xs">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-slate-400">
                <p className="font-medium text-slate-300 mb-1">操作提示</p>
                <p>• 拖拽旋转视角</p>
                <p>• 滚轮缩放</p>
                <p>• 点击节点查看详情</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* 图例 */}
        <div className="absolute top-4 right-4">
          <div className="bg-slate-800/90 backdrop-blur-sm border border-slate-700 rounded-lg p-3">
            <p className="text-xs font-medium text-slate-300 mb-2">图例</p>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-slate-500" />
                <span className="text-xs text-slate-400">普通节点</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <span className="text-xs text-slate-400">隐藏关系节点</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-slate-600" />
                <span className="text-xs text-slate-400">已知关系</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 border-t-2 border-dashed border-yellow-400" />
                <span className="text-xs text-slate-400">隐藏关系</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
