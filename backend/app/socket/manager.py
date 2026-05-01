from typing import Dict, Set, Optional, Any
from datetime import datetime
from enum import Enum
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


class RoomType(Enum):
    DEBATE = "debate"
    ARENA = "arena"


class SocketManager:
    """Socket.IO连接管理器 - 内存房间管理与数据库同步"""
    
    def __init__(self):
        self.debate_rooms: Dict[str, Dict[str, Any]] = {}
        self.arena_rooms: Dict[str, Dict[str, Any]] = {}
        self.user_rooms: Dict[str, Dict[str, Any]] = {}
        self.user_info: Dict[str, Dict] = {}
    
    def _get_db(self):
        from app.database import get_database
        return get_database()
    
    def join_debate_room(
        self, 
        sid: str, 
        debate_id: str, 
        user_info: Optional[Dict] = None
    ) -> int:
        """
        用户加入辩论房间（内存管理）
        
        Args:
            sid: Socket.IO SID
            debate_id: 辩论ID字符串
            user_info: 用户信息
        
        Returns:
            当前房间观众数
        """
        if debate_id not in self.debate_rooms:
            self.debate_rooms[debate_id] = {
                "sids": set(),
                "created_at": datetime.utcnow()
            }
        
        old_count = len(self.debate_rooms[debate_id]["sids"])
        self.debate_rooms[debate_id]["sids"].add(sid)
        new_count = len(self.debate_rooms[debate_id]["sids"])
        
        self.user_rooms[sid] = {
            "room_id": debate_id,
            "room_type": RoomType.DEBATE
        }
        
        if user_info:
            self.user_info[sid] = user_info
        
        logger.info(f"User {sid} joined debate {debate_id}. Count: {old_count} -> {new_count}")
        return new_count
    
    def join_arena_room(
        self, 
        sid: str, 
        room_id: str, 
        user_info: Optional[Dict] = None
    ) -> int:
        """
        用户加入竞技场房间（内存管理）
        
        Args:
            sid: Socket.IO SID
            room_id: 竞技场房间ID
            user_info: 用户信息
        
        Returns:
            当前房间观众数
        """
        if room_id not in self.arena_rooms:
            self.arena_rooms[room_id] = {
                "sids": set(),
                "created_at": datetime.utcnow()
            }
        
        old_count = len(self.arena_rooms[room_id]["sids"])
        self.arena_rooms[room_id]["sids"].add(sid)
        new_count = len(self.arena_rooms[room_id]["sids"])
        
        self.user_rooms[sid] = {
            "room_id": room_id,
            "room_type": RoomType.ARENA
        }
        
        if user_info:
            self.user_info[sid] = user_info
        
        logger.info(f"User {sid} joined arena {room_id}. Count: {old_count} -> {new_count}")
        return new_count
    
    async def leave_debate_room(self, sid: str) -> Optional[Dict[str, Any]]:
        """
        用户离开辩论房间（同步更新内存和数据库）
        
        Returns:
            {"room_id": str, "viewer_count": int} 或 None
        """
        if sid not in self.user_rooms:
            return None
        
        room_info = self.user_rooms.get(sid)
        if not room_info or room_info["room_type"] != RoomType.DEBATE:
            return None
        
        debate_id = room_info["room_id"]
        
        if debate_id in self.debate_rooms:
            self.debate_rooms[debate_id]["sids"].discard(sid)
            new_count = len(self.debate_rooms[debate_id]["sids"])
            
            if not self.debate_rooms[debate_id]["sids"]:
                del self.debate_rooms[debate_id]
            
            await self._sync_debate_viewer_count(debate_id, new_count)
            
            if sid in self.user_rooms:
                del self.user_rooms[sid]
            if sid in self.user_info:
                del self.user_info[sid]
            
            logger.info(f"User {sid} left debate {debate_id}. New count: {new_count}")
            return {
                "room_id": debate_id,
                "viewer_count": new_count
            }
        
        return None
    
    async def leave_arena_room(self, sid: str) -> Optional[Dict[str, Any]]:
        """
        用户离开竞技场房间（同步更新内存和数据库）
        
        Returns:
            {"room_id": str, "viewer_count": int} 或 None
        """
        if sid not in self.user_rooms:
            return None
        
        room_info = self.user_rooms.get(sid)
        if not room_info or room_info["room_type"] != RoomType.ARENA:
            return None
        
        room_id = room_info["room_id"]
        
        if room_id in self.arena_rooms:
            self.arena_rooms[room_id]["sids"].discard(sid)
            new_count = len(self.arena_rooms[room_id]["sids"])
            
            if not self.arena_rooms[room_id]["sids"]:
                del self.arena_rooms[room_id]
            
            await self._sync_arena_viewer_count(room_id, new_count)
            
            if sid in self.user_rooms:
                del self.user_rooms[sid]
            if sid in self.user_info:
                del self.user_info[sid]
            
            logger.info(f"User {sid} left arena {room_id}. New count: {new_count}")
            return {
                "room_id": room_id,
                "viewer_count": new_count
            }
        
        return None
    
    async def leave_any_room(self, sid: str) -> Optional[Dict[str, Any]]:
        """
        用户离开当前所在的任何房间（用于disconnect事件）
        
        Returns:
            {"room_id": str, "room_type": str, "viewer_count": int} 或 None
        """
        room_info = self.user_rooms.get(sid)
        if not room_info:
            return None
        
        room_type = room_info["room_type"]
        room_id = room_info["room_id"]
        
        result = None
        
        if room_type == RoomType.DEBATE:
            result = await self.leave_debate_room(sid)
        elif room_type == RoomType.ARENA:
            result = await self.leave_arena_room(sid)
        
        if result:
            result["room_type"] = room_type.value
        
        return result
    
    async def _sync_debate_viewer_count(self, debate_id: str, count: int):
        """同步辩论房间观众数到数据库"""
        try:
            db = self._get_db()
            if db is None:
                logger.warning(f"Database not available, cannot sync debate {debate_id}")
                return
            
            try:
                debate_oid = ObjectId(debate_id)
            except Exception:
                logger.warning(f"Invalid debate_id format: {debate_id}")
                return
            
            result = await db.debates.update_one(
                {"_id": debate_oid},
                {"$set": {"viewer_count": max(0, count)}}
            )
            
            if result.modified_count > 0:
                logger.debug(f"Synced debate {debate_id} viewer count: {count}")
            else:
                logger.warning(f"Debate {debate_id} not found in database")
                
        except Exception as e:
            logger.error(f"Failed to sync debate viewer count: {e}")
    
    async def _sync_arena_viewer_count(self, room_id: str, count: int):
        """同步竞技场房间观众数到数据库"""
        try:
            db = self._get_db()
            if db is None:
                logger.warning(f"Database not available, cannot sync arena {room_id}")
                return
            
            result = await db.arena_rooms.update_one(
                {"room_id": room_id},
                {"$set": {"viewer_count": max(0, count)}}
            )
            
            if result.modified_count > 0:
                logger.debug(f"Synced arena {room_id} viewer count: {count}")
            else:
                logger.warning(f"Arena room {room_id} not found in database")
                
        except Exception as e:
            logger.error(f"Failed to sync arena viewer count: {e}")
    
    def get_debate_viewers(self, debate_id: str) -> int:
        """获取辩论房间观众数（从内存）"""
        if debate_id in self.debate_rooms:
            return len(self.debate_rooms[debate_id]["sids"])
        return 0
    
    def get_arena_viewers(self, room_id: str) -> int:
        """获取竞技场房间观众数（从内存）"""
        if room_id in self.arena_rooms:
            return len(self.arena_rooms[room_id]["sids"])
        return 0
    
    def get_user_room(self, sid: str) -> Optional[Dict[str, Any]]:
        """获取用户所在房间信息"""
        return self.user_rooms.get(sid)
    
    def get_user_info(self, sid: str) -> Optional[Dict]:
        """获取用户信息"""
        return self.user_info.get(sid)
    
    def set_user_info(self, sid: str, user_info: Dict):
        """设置用户信息"""
        self.user_info[sid] = user_info
    
    def get_all_active_debates(self) -> Dict[str, int]:
        """获取所有活跃辩论及其观众数"""
        return {
            debate_id: len(room["sids"])
            for debate_id, room in self.debate_rooms.items()
        }
    
    def get_all_active_arenas(self) -> Dict[str, int]:
        """获取所有活跃竞技场房间及其观众数"""
        return {
            room_id: len(room["sids"])
            for room_id, room in self.arena_rooms.items()
        }
    
    async def sync_all_rooms_to_db(self):
        """将所有内存房间状态同步到数据库（用于启动时或定期同步）"""
        for debate_id, room in self.debate_rooms.items():
            count = len(room["sids"])
            await self._sync_debate_viewer_count(debate_id, count)
        
        for room_id, room in self.arena_rooms.items():
            count = len(room["sids"])
            await self._sync_arena_viewer_count(room_id, count)
        
        logger.info("All room viewer counts synced to database")


socket_manager = SocketManager()


def get_socket_manager() -> SocketManager:
    """获取Socket管理器实例"""
    return socket_manager
