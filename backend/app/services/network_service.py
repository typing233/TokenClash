import networkx as nx
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from app.database import get_database
from app.config import get_settings

settings = get_settings()


class NetworkService:
    """Token关系网络服务"""
    
    def __init__(self):
        self.db = None
        self._graph: Optional[nx.Graph] = None
        self._graph_updated_at: Optional[datetime] = None
    
    def get_db(self):
        """获取数据库实例"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    def get_graph(self) -> nx.Graph:
        """获取图实例"""
        if self._graph is None:
            self._graph = nx.Graph()
        return self._graph
    
    async def build_graph_from_debates(self) -> nx.Graph:
        """从历史辩论构建关系图"""
        db = self.get_db()
        G = self.get_graph()
        G.clear()
        
        cursor = db.debates.find({
            "stage": "finished"
        }).sort("created_at", -1).limit(100)
        
        debate_count = 0
        async for debate in cursor:
            debate_count += 1
            participants = debate.get("participants", [])
            
            if len(participants) < 2:
                continue
            
            model_ids = [p.get("model_id") or p.get("id") for p in participants]
            model_names = [p.get("display_name") or p.get("model_name") for p in participants]
            
            for i, model_id in enumerate(model_ids):
                if model_id:
                    if not G.has_node(model_id):
                        G.add_node(
                            model_id,
                            name=model_names[i] or model_id,
                            debate_count=0,
                            wins=0,
                            losses=0
                        )
                    
                    G.nodes[model_id]["debate_count"] += 1
            
            winner = debate.get("winner")
            vote_results = debate.get("vote_results", {})
            
            for i in range(len(model_ids)):
                for j in range(i + 1, len(model_ids)):
                    if model_ids[i] and model_ids[j]:
                        if not G.has_edge(model_ids[i], model_ids[j]):
                            G.add_edge(
                                model_ids[i],
                                model_ids[j],
                                weight=0,
                                debates=[],
                                win_loss_records={}
                            )
                        
                        edge_data = G[model_ids[i]][model_ids[j]]
                        edge_data["weight"] += 1
                        edge_data["debates"].append({
                            "debate_id": str(debate.get("_id")),
                            "title": debate.get("title"),
                            "timestamp": debate.get("created_at", datetime.utcnow()).isoformat() if hasattr(debate.get("created_at"), 'isoformat') else str(debate.get("created_at"))
                        })
                        
                        if winner:
                            if winner == model_ids[i]:
                                G.nodes[model_ids[i]]["wins"] = G.nodes[model_ids[i]].get("wins", 0) + 1
                                G.nodes[model_ids[j]]["losses"] = G.nodes[model_ids[j]].get("losses", 0) + 1
                            elif winner == model_ids[j]:
                                G.nodes[model_ids[j]]["wins"] = G.nodes[model_ids[j]].get("wins", 0) + 1
                                G.nodes[model_ids[i]]["losses"] = G.nodes[model_ids[i]].get("losses", 0) + 1
        
        await self._save_graph_to_db(G)
        self._graph_updated_at = datetime.utcnow()
        
        return G
    
    async def _save_graph_to_db(self, G: nx.Graph):
        """保存图到数据库"""
        db = self.get_db()
        
        nodes_data = []
        for node_id, attrs in G.nodes(data=True):
            nodes_data.append({
                "node_id": node_id,
                "name": attrs.get("name", node_id),
                "debate_count": attrs.get("debate_count", 0),
                "wins": attrs.get("wins", 0),
                "losses": attrs.get("losses", 0),
                "attributes": {k: v for k, v in attrs.items() if k not in ["name", "debate_count", "wins", "losses"]}
            })
        
        edges_data = []
        for u, v, attrs in G.edges(data=True):
            edges_data.append({
                "source": u,
                "target": v,
                "weight": attrs.get("weight", 1),
                "debates": attrs.get("debates", []),
                "attributes": {k: v for k, v in attrs.items() if k not in ["weight", "debates"]}
            })
        
        await db.network_nodes.delete_many({})
        await db.network_edges.delete_many({})
        
        if nodes_data:
            await db.network_nodes.insert_many(nodes_data)
        if edges_data:
            await db.network_edges.insert_many(edges_data)
    
    async def load_graph_from_db(self) -> nx.Graph:
        """从数据库加载图"""
        db = self.get_db()
        G = self.get_graph()
        G.clear()
        
        nodes_cursor = db.network_nodes.find()
        async for node_doc in nodes_cursor:
            G.add_node(
                node_doc["node_id"],
                name=node_doc.get("name", node_doc["node_id"]),
                debate_count=node_doc.get("debate_count", 0),
                wins=node_doc.get("wins", 0),
                losses=node_doc.get("losses", 0),
                **(node_doc.get("attributes", {}))
            )
        
        edges_cursor = db.network_edges.find()
        async for edge_doc in edges_cursor:
            G.add_edge(
                edge_doc["source"],
                edge_doc["target"],
                weight=edge_doc.get("weight", 1),
                debates=edge_doc.get("debates", []),
                **(edge_doc.get("attributes", {}))
            )
        
        self._graph_updated_at = datetime.utcnow()
        return G
    
    async def get_or_load_graph(self, force_rebuild: bool = False) -> nx.Graph:
        """获取或加载图"""
        G = self.get_graph()
        
        if force_rebuild or G.number_of_nodes() == 0:
            G = await self.load_graph_from_db()
            if G.number_of_nodes() == 0:
                G = await self.build_graph_from_debates()
        
        return G
    
    def calculate_adamic_adar_index(self, G: nx.Graph, u: str, v: str) -> float:
        """计算Adamic-Adar指数"""
        try:
            preds = list(nx.adamic_adar_index(G, [(u, v)]))
            if preds:
                return preds[0][2]
            return 0.0
        except Exception:
            return 0.0
    
    async def find_hidden_relationships(
        self,
        limit: int = 20,
        min_score: float = 0.1
    ) -> List[Dict[str, Any]]:
        """发现隐藏的Token对（看似无关但共享很多邻居）"""
        G = await self.get_or_load_graph()
        
        if G.number_of_nodes() < 2:
            return []
        
        all_nodes = list(G.nodes())
        hidden_pairs = []
        
        for i in range(len(all_nodes)):
            for j in range(i + 1, len(all_nodes)):
                u, v = all_nodes[i], all_nodes[j]
                
                if G.has_edge(u, v):
                    continue
                
                score = self.calculate_adamic_adar_index(G, u, v)
                
                if score >= min_score:
                    u_neighbors = set(G.neighbors(u))
                    v_neighbors = set(G.neighbors(v))
                    common_neighbors = list(u_neighbors & v_neighbors)
                    
                    hidden_pairs.append({
                        "model1_id": u,
                        "model1_name": G.nodes[u].get("name", u),
                        "model2_id": v,
                        "model2_name": G.nodes[v].get("name", v),
                        "adamic_adar_score": score,
                        "common_neighbors_count": len(common_neighbors),
                        "common_neighbors": [
                            {
                                "model_id": n,
                                "name": G.nodes[n].get("name", n)
                            }
                            for n in common_neighbors[:10]
                        ]
                    })
        
        hidden_pairs.sort(key=lambda x: x["adamic_adar_score"], reverse=True)
        
        return hidden_pairs[:limit]
    
    async def get_graph_data(self) -> Dict[str, Any]:
        """获取图数据用于前端可视化"""
        G = await self.get_or_load_graph()
        
        nodes = []
        for node_id, attrs in G.nodes(data=True):
            degree = G.degree(node_id)
            wins = attrs.get("wins", 0)
            losses = attrs.get("losses", 0)
            total = wins + losses
            win_rate = wins / total if total > 0 else 0.5
            
            nodes.append({
                "id": node_id,
                "name": attrs.get("name", node_id),
                "debate_count": attrs.get("debate_count", 0),
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "degree": degree,
                "size": max(5, min(20, degree * 2 + 5)),
                "group": self._determine_group(G, node_id)
            })
        
        edges = []
        for u, v, attrs in G.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "weight": attrs.get("weight", 1),
                "debate_count": attrs.get("weight", 1),
                "debates": attrs.get("debates", [])
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "avg_degree": sum(n["degree"] for n in nodes) / len(nodes) if nodes else 0
            }
        }
    
    def _determine_group(self, G: nx.Graph, node_id: str) -> int:
        """确定节点所属的社区/组别"""
        try:
            communities = nx.community.greedy_modularity_communities(G)
            for i, community in enumerate(communities):
                if node_id in community:
                    return i
        except Exception:
            pass
        
        return hash(node_id) % 5
    
    async def get_node_detail(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取节点详情"""
        G = await self.get_or_load_graph()
        
        if model_id not in G.nodes():
            return None
        
        attrs = G.nodes[model_id]
        neighbors = list(G.neighbors(model_id))
        
        neighbor_details = []
        for neighbor in neighbors:
            edge_data = G[model_id][neighbor]
            neighbor_details.append({
                "model_id": neighbor,
                "name": G.nodes[neighbor].get("name", neighbor),
                "debate_count": edge_data.get("weight", 1),
                "debates": edge_data.get("debates", [])[:5]
            })
        
        return {
            "model_id": model_id,
            "name": attrs.get("name", model_id),
            "debate_count": attrs.get("debate_count", 0),
            "wins": attrs.get("wins", 0),
            "losses": attrs.get("losses", 0),
            "degree": G.degree(model_id),
            "neighbors": neighbor_details,
            "neighbor_count": len(neighbors)
        }
    
    async def add_relationship(
        self,
        model1_id: str,
        model2_id: str,
        metadata: Optional[Dict] = None
    ):
        """添加两个Token之间的关系"""
        G = await self.get_or_load_graph()
        
        if not G.has_node(model1_id):
            G.add_node(model1_id, name=model1_id, debate_count=0, wins=0, losses=0)
        if not G.has_node(model2_id):
            G.add_node(model2_id, name=model2_id, debate_count=0, wins=0, losses=0)
        
        if G.has_edge(model1_id, model2_id):
            G[model1_id][model2_id]["weight"] += 1
        else:
            G.add_edge(model1_id, model2_id, weight=1, debates=[])
        
        if metadata:
            debates = G[model1_id][model2_id].get("debates", [])
            debates.append(metadata)
            G[model1_id][model2_id]["debates"] = debates
        
        await self._save_graph_to_db(G)


network_service = NetworkService()


def get_network_service() -> NetworkService:
    """获取网络服务实例"""
    return network_service
