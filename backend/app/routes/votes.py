from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from app.database import get_database
from app.models.vote import Vote, VoteCreate, VoteResult
from app.models.debate import Debate
from app.services.ranking_service import get_ranking_service


router = APIRouter()


@router.post("/", response_model=Vote)
async def create_vote(vote_data: VoteCreate):
    """
    创建投票
    
    Args:
        vote_data: 投票数据
    """
    db = get_database()
    
    # 检查辩论是否存在且处于投票阶段
    try:
        debate_id = ObjectId(vote_data.debate_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid debate ID")
    
    debate = await db.debates.find_one({"_id": debate_id})
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    if debate["stage"] != "voting" and debate["stage"] != "finished":
        raise HTTPException(
            status_code=400, 
            detail=f"Voting is not allowed in stage: {debate['stage']}"
        )
    
    # 检查用户是否已经投过票（如果有user_id的话）
    if vote_data.user_id:
        existing_vote = await db.votes.find_one({
            "debate_id": debate_id,
            "user_id": vote_data.user_id,
            "is_valid": True
        })
        if existing_vote:
            raise HTTPException(status_code=400, detail="You have already voted")
    
    # 验证评分范围（1-10分）
    def validate_scores(scores: Dict, participants: List):
        model_ids = [p["model_id"] for p in participants]
        for model_id, score in scores.items():
            if model_id not in model_ids:
                raise HTTPException(status_code=400, detail=f"Invalid model ID: {model_id}")
            if not (1 <= score <= 10):
                raise HTTPException(status_code=400, detail="Score must be between 1 and 10")
    
    participants = debate.get("participants", [])
    validate_scores(vote_data.logic_score, participants)
    validate_scores(vote_data.persuasion_score, participants)
    validate_scores(vote_data.humor_score, participants)
    
    # 准备投票数据
    vote_dict = vote_data.model_dump()
    vote_dict["debate_id"] = debate_id
    vote_dict["created_at"] = datetime.utcnow()
    vote_dict["is_valid"] = True
    
    # 插入数据库
    result = await db.votes.insert_one(vote_dict)
    vote_dict["_id"] = result.inserted_id
    
    return Vote(**vote_dict)


@router.get("/debate/{debate_id}")
async def get_debate_votes(
    debate_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    获取辩论的所有投票
    
    Args:
        debate_id: 辩论ID
        skip: 跳过数量
        limit: 返回数量限制
    """
    db = get_database()
    
    try:
        obj_id = ObjectId(debate_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid debate ID")
    
    cursor = db.votes.find(
        {"debate_id": obj_id, "is_valid": True}
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    votes = await cursor.to_list(length=limit)
    
    return {"votes": [Vote(**vote) for vote in votes], "total": len(votes)}


@router.get("/debate/{debate_id}/result", response_model=VoteResult)
async def get_debate_vote_result(debate_id: str):
    """
    获取辩论的投票结果统计
    
    Args:
        debate_id: 辩论ID
    """
    try:
        obj_id = ObjectId(debate_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid debate ID")
    
    ranking_service = get_ranking_service()
    result = await ranking_service.calculate_debate_result(obj_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="No votes found or debate not found")
    
    return result


@router.get("/user/{user_id}")
async def get_user_votes(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    获取用户的投票历史
    
    Args:
        user_id: 用户ID
        skip: 跳过数量
        limit: 返回数量限制
    """
    db = get_database()
    
    cursor = db.votes.find(
        {"user_id": user_id, "is_valid": True}
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    votes = await cursor.to_list(length=limit)
    
    return {"votes": [Vote(**vote) for vote in votes], "total": len(votes)}


@router.delete("/{vote_id}")
async def delete_vote(vote_id: str):
    """
    删除投票（软删除）
    
    Args:
        vote_id: 投票ID
    """
    db = get_database()
    
    try:
        obj_id = ObjectId(vote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid vote ID")
    
    # 软删除
    result = await db.votes.update_one(
        {"_id": obj_id},
        {"$set": {"is_valid": False}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vote not found")
    
    return {"message": "Vote deleted successfully"}


@router.get("/statistics/overview")
async def get_voting_statistics():
    """获取投票统计概览"""
    db = get_database()
    
    # 总投票数
    total_votes = await db.votes.count_documents({"is_valid": True})
    
    # 参与投票的用户数
    pipeline = [
        {"$match": {"is_valid": True, "user_id": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "unique_users"}
    ]
    
    result = await db.votes.aggregate(pipeline).to_list(length=1)
    unique_users = result[0]["unique_users"] if result else 0
    
    # 按分类统计
    pipeline = [
        {"$match": {"is_valid": True}},
        {"$lookup": {
            "from": "debates",
            "localField": "debate_id",
            "foreignField": "_id",
            "as": "debate"
        }},
        {"$unwind": "$debate"},
        {"$group": {
            "_id": {"$ifNull": ["$debate.category", "general"]},
            "count": {"$sum": 1}
        }}
    ]
    
    category_stats = await db.votes.aggregate(pipeline).to_list(length=None)
    
    return {
        "total_votes": total_votes,
        "unique_users": unique_users,
        "category_statistics": [
            {"category": stat["_id"], "count": stat["count"]}
            for stat in category_stats
        ]
    }
