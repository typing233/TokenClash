from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.network_service import get_network_service

router = APIRouter()
network_service = get_network_service()


@router.get("/graph")
async def get_graph():
    """获取关系图数据"""
    graph_data = await network_service.get_graph_data()
    return graph_data


@router.post("/graph/rebuild")
async def rebuild_graph():
    """重新从历史辩论构建关系图"""
    G = await network_service.build_graph_from_debates()
    return {
        "success": True,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges()
    }


@router.get("/nodes/{model_id}")
async def get_node_detail(model_id: str):
    """获取节点详情"""
    detail = await network_service.get_node_detail(model_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Node not found: {model_id}")
    return detail


@router.get("/adamic-adar")
async def get_adamic_adar_pairs(
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(0.1, ge=0.0, le=1.0)
):
    """获取隐藏Token对（基于Adamic-Adar指数）"""
    pairs = await network_service.find_hidden_relationships(
        limit=limit,
        min_score=min_score
    )
    return {
        "hidden_pairs": pairs,
        "count": len(pairs)
    }


@router.get("/relationships/{model_id}")
async def get_relationships(model_id: str):
    """获取指定Token的所有关系"""
    detail = await network_service.get_node_detail(model_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Node not found: {model_id}")
    
    return {
        "model_id": model_id,
        "name": detail.get("name"),
        "relationships": detail.get("neighbors", []),
        "relationship_count": detail.get("neighbor_count", 0)
    }


@router.post("/relationships")
async def add_relationship(
    model1_id: str,
    model2_id: str,
    debate_id: Optional[str] = None,
    debate_title: Optional[str] = None
):
    """添加两个Token之间的关系"""
    metadata = {}
    if debate_id:
        metadata["debate_id"] = debate_id
    if debate_title:
        metadata["title"] = debate_title
    
    await network_service.add_relationship(
        model1_id=model1_id,
        model2_id=model2_id,
        metadata=metadata if metadata else None
    )
    
    return {
        "success": True,
        "message": f"Relationship added between {model1_id} and {model2_id}"
    }
