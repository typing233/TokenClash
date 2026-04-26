from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from app.database import get_database
from app.models.topic import Topic, TopicCreate, TopicUpdate, PyObjectId


router = APIRouter()


@router.get("/", response_model=List[Topic])
async def get_topics(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """
    获取话题列表
    
    Args:
        skip: 跳过数量
        limit: 返回数量限制
        category: 分类筛选
        is_active: 是否活跃筛选
    """
    db = get_database()
    
    query = {}
    if category:
        query["category"] = category
    if is_active is not None:
        query["is_active"] = is_active
    
    cursor = db.topics.find(query).sort("created_at", -1).skip(skip).limit(limit)
    topics = await cursor.to_list(length=limit)
    
    return [Topic(**topic) for topic in topics]


@router.get("/{topic_id}", response_model=Topic)
async def get_topic(topic_id: str):
    """
    获取单个话题详情
    
    Args:
        topic_id: 话题ID
    """
    db = get_database()
    
    try:
        obj_id = ObjectId(topic_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid topic ID")
    
    topic = await db.topics.find_one({"_id": obj_id})
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return Topic(**topic)


@router.post("/", response_model=Topic)
async def create_topic(topic_data: TopicCreate):
    """
    创建新话题
    
    Args:
        topic_data: 话题数据
    """
    db = get_database()
    
    # 准备话题数据
    topic_dict = topic_data.model_dump()
    topic_dict["created_at"] = datetime.utcnow()
    topic_dict["updated_at"] = datetime.utcnow()
    topic_dict["debate_count"] = 0
    topic_dict["is_active"] = True
    
    # 插入数据库
    result = await db.topics.insert_one(topic_dict)
    topic_dict["_id"] = result.inserted_id
    
    return Topic(**topic_dict)


@router.put("/{topic_id}", response_model=Topic)
async def update_topic(topic_id: str, update_data: TopicUpdate):
    """
    更新话题
    
    Args:
        topic_id: 话题ID
        update_data: 更新数据
    """
    db = get_database()
    
    try:
        obj_id = ObjectId(topic_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid topic ID")
    
    # 准备更新数据
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_dict["updated_at"] = datetime.utcnow()
    
    # 执行更新
    result = await db.topics.update_one(
        {"_id": obj_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # 获取更新后的话题
    topic = await db.topics.find_one({"_id": obj_id})
    return Topic(**topic)


@router.delete("/{topic_id}")
async def delete_topic(topic_id: str):
    """
    删除话题（软删除）
    
    Args:
        topic_id: 话题ID
    """
    db = get_database()
    
    try:
        obj_id = ObjectId(topic_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid topic ID")
    
    # 软删除：设置is_active为False
    result = await db.topics.update_one(
        {"_id": obj_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return {"message": "Topic deleted successfully"}


@router.get("/categories/list")
async def get_categories():
    """获取所有话题分类"""
    db = get_database()
    
    # 使用聚合获取所有唯一分类
    pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    results = await db.topics.aggregate(pipeline).to_list(length=None)
    
    categories = [
        {"name": result["_id"] or "general", "count": result["count"]}
        for result in results
    ]
    
    return {"categories": categories}


@router.get("/hot/trending")
async def get_hot_topics(limit: int = Query(10, ge=1, le=50)):
    """
    获取热门话题（按辩论数量排序）
    
    Args:
        limit: 返回数量限制
    """
    db = get_database()
    
    cursor = db.topics.find(
        {"is_active": True}
    ).sort("debate_count", -1).limit(limit)
    
    topics = await cursor.to_list(length=limit)
    
    return {"hot_topics": [Topic(**topic) for topic in topics]}
