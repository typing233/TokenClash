from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.arena import CreateRoomRequest, UseSkillRequest, CastVoteRequest, AddEnergyRequest
from app.services.arena_service import get_arena_service
from app.config import get_settings

router = APIRouter()
arena_service = get_arena_service()
settings = get_settings()


@router.get("/rooms")
async def get_active_rooms():
    """获取所有活跃的竞技场房间"""
    rooms = await arena_service.get_active_rooms()
    return {
        "rooms": [room.to_dict() for room in rooms],
        "count": len(rooms)
    }


@router.post("/rooms")
async def create_room(request: CreateRoomRequest):
    """创建新的竞技场房间"""
    room = await arena_service.create_room(
        request=request,
        model_configs=settings.model_configs
    )
    return {
        "success": True,
        "room": room.to_dict()
    }


@router.get("/rooms/{room_id}")
async def get_room(room_id: str):
    """获取房间详情"""
    room = await arena_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room not found: {room_id}")
    return room.to_dict()


@router.post("/rooms/{room_id}/start")
async def start_room(room_id: str):
    """开始房间倒计时"""
    success = await arena_service.start_room(room_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Room not found: {room_id}")
    return {
        "success": True,
        "message": "Arena started"
    }


@router.post("/rooms/{room_id}/skills")
async def use_skill(room_id: str, request: UseSkillRequest):
    """使用技能卡"""
    result = await arena_service.use_skill(
        room_id=room_id,
        skill_id=request.skill_id,
        target_model_id=request.target_model_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to use skill"))
    
    return result


@router.post("/rooms/{room_id}/vote")
async def cast_vote(room_id: str, request: CastVoteRequest):
    """投票"""
    result = await arena_service.cast_vote(
        room_id=room_id,
        model_id=request.model_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to cast vote"))
    
    return result


@router.post("/rooms/{room_id}/energy")
async def add_energy(room_id: str, request: AddEnergyRequest):
    """充能量"""
    result = await arena_service.add_energy(
        room_id=room_id,
        model_id=request.model_id,
        amount=request.amount
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to add energy"))
    
    return result


@router.get("/skills")
async def get_available_skills():
    """获取所有可用的技能卡"""
    skills = arena_service.get_default_skills()
    return {
        "skills": [skill.model_dump() for skill in skills],
        "count": len(skills)
    }
