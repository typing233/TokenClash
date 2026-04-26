from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from app.database import get_database
from app.models.debate import Debate, DebateCreate, DebateUpdate, DebateStage
from app.models.topic import PyObjectId
from app.services.debate_engine import get_debate_engine
from app.config import get_settings
from app.socket_instance import sio


router = APIRouter()
settings = get_settings()


@router.get("/", response_model=List[Debate])
async def get_debates(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    stage: Optional[str] = None,
    topic_id: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """
    获取辩论列表
    
    Args:
        skip: 跳过数量
        limit: 返回数量限制
        stage: 阶段筛选
        topic_id: 话题ID筛选
        is_active: 是否活跃筛选
    """
    db = get_database()
    
    query = {}
    if stage:
        query["stage"] = stage
    if topic_id:
        try:
            query["topic_id"] = ObjectId(topic_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid topic ID")
    if is_active is not None:
        query["is_active"] = is_active
    
    cursor = db.debates.find(query).sort("created_at", -1).skip(skip).limit(limit)
    debates = await cursor.to_list(length=limit)
    
    return [Debate(**debate) for debate in debates]


@router.get("/{debate_id}", response_model=Debate)
async def get_debate(debate_id: str):
    """
    获取单个辩论详情
    
    Args:
        debate_id: 辩论ID
    """
    db = get_database()
    
    try:
        obj_id = ObjectId(debate_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid debate ID")
    
    debate = await db.debates.find_one({"_id": obj_id})
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    return Debate(**debate)


@router.post("/", response_model=Debate)
async def create_debate(debate_data: DebateCreate):
    """
    创建新辩论
    
    Args:
        debate_data: 辩论数据
    """
    debate_engine = get_debate_engine()
    
    # 验证参与者
    participants = debate_data.participants
    if len(participants) != 2:
        raise HTTPException(status_code=400, detail="Debate must have exactly 2 participants")
    
    # 检查立场是否正确
    sides = [p.side for p in participants]
    if "affirmative" not in sides or "negative" not in sides:
        raise HTTPException(status_code=400, detail="Debate must have one affirmative and one negative participant")
    
    # 调用辩论引擎创建辩论
    try:
        debate = await debate_engine.create_debate(
            topic_id=debate_data.topic_id,
            title=debate_data.title,
            participants=[p.model_dump() for p in participants],
            max_rounds=debate_data.max_rounds,
            category=debate_data.category or "general"
        )
        return debate
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{debate_id}/start")
async def start_debate(debate_id: str):
    """
    开始辩论
    
    Args:
        debate_id: 辩论ID
    """
    db = get_database()
    debate_engine = get_debate_engine()
    
    try:
        obj_id = ObjectId(debate_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid debate ID")
    
    # 检查辩论状态
    debate = await db.debates.find_one({"_id": obj_id})
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    if debate["stage"] != "waiting":
        raise HTTPException(status_code=400, detail=f"Debate is already in stage: {debate['stage']}")
    
    # 开始辩论
    success = await debate_engine.start_debate(obj_id, sio)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start debate")
    
    return {"message": "Debate started successfully", "debate_id": debate_id}


@router.put("/{debate_id}", response_model=Debate)
async def update_debate(debate_id: str, update_data: DebateUpdate):
    """
    更新辩论
    
    Args:
        debate_id: 辩论ID
        update_data: 更新数据
    """
    db = get_database()
    
    try:
        obj_id = ObjectId(debate_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid debate ID")
    
    # 准备更新数据
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # 执行更新
    result = await db.debates.update_one(
        {"_id": obj_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    # 获取更新后的辩论
    debate = await db.debates.find_one({"_id": obj_id})
    return Debate(**debate)


@router.get("/{debate_id}/messages")
async def get_debate_messages(
    debate_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    message_type: Optional[str] = None
):
    """
    获取辩论的消息历史
    
    Args:
        debate_id: 辩论ID
        skip: 跳过数量
        limit: 返回数量限制
        message_type: 消息类型筛选
    """
    db = get_database()
    
    try:
        obj_id = ObjectId(debate_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid debate ID")
    
    query = {"debate_id": obj_id}
    if message_type:
        query["message_type"] = message_type
    
    cursor = db.messages.find(query).sort("created_at", 1).skip(skip).limit(limit)
    messages = await cursor.to_list(length=limit)
    
    # 转换ObjectId为字符串
    for msg in messages:
        msg["_id"] = str(msg["_id"])
        msg["debate_id"] = str(msg["debate_id"])
    
    return {"messages": messages, "total": len(messages)}


@router.get("/live/active")
async def get_active_debates():
    """获取当前活跃的辩论（正在进行中的）"""
    db = get_database()
    
    # 查询正在进行中的辩论
    active_stages = ["opening", "cross_examination", "closing", "voting"]
    cursor = db.debates.find(
        {"stage": {"$in": active_stages}, "is_active": True}
    ).sort("created_at", -1)
    
    debates = await cursor.to_list(length=None)
    
    return {
        "active_debates": [Debate(**debate) for debate in debates],
        "count": len(debates)
    }


@router.get("/available/models")
async def get_available_models():
    """获取可用的模型列表（用于创建辩论时选择）"""
    from app.config import get_settings
    settings = get_settings()
    
    models = []
    for model_id, config in settings.model_configs.items():
        models.append({
            "model_id": model_id,
            "model_name": config["model_name"],
            "display_name": config["display_name"]
        })
    
    return {"available_models": models}
