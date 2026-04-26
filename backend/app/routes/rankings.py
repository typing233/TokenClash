from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.ranking_service import get_ranking_service
from app.models.model_stats import OverallRanking, CategoryRanking, ModelStats


router = APIRouter()


@router.get("/overall", response_model=OverallRanking)
async def get_overall_ranking(
    limit: int = Query(20, ge=1, le=100)
):
    """
    获取总体排行榜
    
    Args:
        limit: 返回数量限制
    """
    ranking_service = get_ranking_service()
    ranking = await ranking_service.get_overall_ranking(limit=limit)
    return ranking


@router.get("/category/{category}", response_model=CategoryRanking)
async def get_category_ranking(
    category: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    获取分类排行榜
    
    Args:
        category: 分类名称
        limit: 返回数量限制
    """
    ranking_service = get_ranking_service()
    ranking = await ranking_service.get_category_ranking(category, limit=limit)
    
    if not ranking:
        raise HTTPException(status_code=404, detail=f"No ranking data found for category: {category}")
    
    return ranking


@router.get("/model/{model_id}", response_model=ModelStats)
async def get_model_stats(model_id: str):
    """
    获取单个模型的详细统计数据
    
    Args:
        model_id: 模型ID
    """
    ranking_service = get_ranking_service()
    stats = await ranking_service.get_model_stats(model_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail=f"Model stats not found for: {model_id}")
    
    return stats


@router.get("/categories/list")
async def get_all_categories():
    """获取所有有数据的分类列表"""
    ranking_service = get_ranking_service()
    categories = await ranking_service.get_all_categories()
    
    return {"categories": categories}


@router.get("/trending/rising")
async def get_rising_models(limit: int = Query(10, ge=1, le=50)):
    """
    获取上升趋势的模型（基于最近表现）
    
    Args:
        limit: 返回数量限制
    """
    from app.database import get_database
    
    db = get_database()
    
    # 查找最近10场表现中胜率上升的模型
    pipeline = [
        {"$match": {"total_debates": {"$gte": 5}}},  # 至少参加5场
        {"$addFields": {
            "recent_wins": {
                "$size": {
                    "$filter": {
                        "input": "$recent_performance",
                        "as": "p",
                        "cond": {"$eq": ["$$p.result", "win"]}
                    }
                }
            },
            "recent_total": {"$size": "$recent_performance"}
        }},
        {"$addFields": {
            "recent_win_rate": {
                "$cond": {
                    "if": {"$gt": ["$recent_total", 0]},
                    "then": {"$divide": ["$recent_wins", "$recent_total"]},
                    "else": 0
                }
            }
        }},
        {"$sort": {"recent_win_rate": -1, "win_rate": -1}},
        {"$limit": limit}
    ]
    
    results = await db.model_stats.aggregate(pipeline).to_list(length=limit)
    
    # 转换为响应格式
    rising_models = []
    for result in results:
        rising_models.append({
            "model_id": result["model_id"],
            "model_name": result["model_name"],
            "display_name": result["display_name"],
            "win_rate": result["win_rate"],
            "recent_win_rate": result.get("recent_win_rate", 0),
            "total_debates": result["total_debates"],
            "style_tags": result.get("style_tags", [])
        })
    
    return {"rising_models": rising_models}


@router.get("/statistics/comparison")
async def compare_models(model_ids: str = Query(..., description="逗号分隔的模型ID列表")):
    """
    比较多个模型的表现
    
    Args:
        model_ids: 逗号分隔的模型ID列表，如 "model_1,model_2"
    """
    from app.database import get_database
    from bson.objectid import ObjectId
    
    db = get_database()
    
    # 解析模型ID
    model_id_list = [mid.strip() for mid in model_ids.split(",") if mid.strip()]
    
    if len(model_id_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 model IDs are required for comparison")
    
    # 查询模型统计
    cursor = db.model_stats.find({"model_id": {"$in": model_id_list}})
    models_stats = await cursor.to_list(length=len(model_id_list))
    
    if len(models_stats) < 2:
        raise HTTPException(status_code=404, detail="Not enough model data found for comparison")
    
    # 准备比较数据
    comparison = {
        "models": [],
        "comparison_metrics": {
            "win_rate": {},
            "total_debates": {},
            "avg_logic_score": {},
            "avg_persuasion_score": {},
            "avg_humor_score": {},
            "avg_overall_score": {}
        }
    }
    
    for stats in models_stats:
        model_info = {
            "model_id": stats["model_id"],
            "model_name": stats["model_name"],
            "display_name": stats["display_name"],
            "win_rate": stats["win_rate"],
            "total_debates": stats["total_debates"],
            "avg_logic_score": stats["avg_logic_score"],
            "avg_persuasion_score": stats["avg_persuasion_score"],
            "avg_humor_score": stats["avg_humor_score"],
            "avg_overall_score": stats["avg_overall_score"],
            "style_tags": stats.get("style_tags", []),
            "category_stats": stats.get("category_stats", {})
        }
        
        comparison["models"].append(model_info)
        
        # 填充比较指标
        mid = stats["model_id"]
        comparison["comparison_metrics"]["win_rate"][mid] = stats["win_rate"]
        comparison["comparison_metrics"]["total_debates"][mid] = stats["total_debates"]
        comparison["comparison_metrics"]["avg_logic_score"][mid] = stats["avg_logic_score"]
        comparison["comparison_metrics"]["avg_persuasion_score"][mid] = stats["avg_persuasion_score"]
        comparison["comparison_metrics"]["avg_humor_score"][mid] = stats["avg_humor_score"]
        comparison["comparison_metrics"]["avg_overall_score"][mid] = stats["avg_overall_score"]
    
    return comparison


@router.get("/statistics/overview")
async def get_ranking_overview():
    """获取排行榜统计概览"""
    from app.database import get_database
    
    db = get_database()
    
    # 总模型数
    total_models = await db.model_stats.count_documents({})
    
    # 总辩论数
    total_debates = await db.debates.count_documents({})
    
    # 总投票数
    total_votes = await db.votes.count_documents({"is_valid": True})
    
    # 平均胜率
    pipeline = [
        {"$group": {"_id": None, "avg_win_rate": {"$avg": "$win_rate"}}}
    ]
    result = await db.model_stats.aggregate(pipeline).to_list(length=1)
    avg_win_rate = result[0]["avg_win_rate"] if result else 0
    
    # 风格标签分布
    pipeline = [
        {"$unwind": "$style_tags"},
        {"$group": {"_id": "$style_tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    style_distribution = await db.model_stats.aggregate(pipeline).to_list(length=None)
    
    return {
        "total_models": total_models,
        "total_debates": total_debates,
        "total_votes": total_votes,
        "average_win_rate": round(avg_win_rate, 2),
        "style_distribution": [
            {"style": s["_id"], "count": s["count"]}
            for s in style_distribution
        ]
    }
