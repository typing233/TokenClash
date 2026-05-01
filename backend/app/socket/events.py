from datetime import datetime
from typing import Dict, Optional
from bson import ObjectId
import socketio
from app.database import get_database
from app.models.message import DanmakuCreate
from app.socket.manager import get_socket_manager
import logging

logger = logging.getLogger(__name__)


def _make_serializable(obj):
    """将包含ObjectId/datetime的对象转换为JSON可序列化格式"""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def setup_socket_events(sio: socketio.AsyncServer):
    """设置Socket.IO事件处理"""
    
    @sio.event
    async def connect(sid, environ):
        """客户端连接事件"""
        print(f"Client connected: {sid}")
        await sio.emit("connected", {"sid": sid, "message": "Connected successfully"}, room=sid)
    
    @sio.event
    async def disconnect(sid):
        """客户端断开连接事件"""
        logger.info(f"Client disconnected: {sid}")
        
        socket_manager = get_socket_manager()
        
        room_result = await socket_manager.leave_any_room(sid)
        
        if room_result:
            room_id = room_result["room_id"]
            viewer_count = room_result["viewer_count"]
            room_type = room_result["room_type"]
            
            await sio.leave_room(sid, room_id)
            
            event_name = "user_left" if room_type == "debate" else "user_left_arena"
            
            await sio.emit(
                event_name,
                {
                    "sid": sid,
                    "room_id": room_id,
                    "viewer_count": viewer_count
                },
                room=room_id
            )
            
            logger.info(f"Client {sid} disconnected from {room_type} room {room_id}, new viewer count: {viewer_count}")
    
    @sio.event
    async def join_debate(sid, data):
        """
        加入辩论直播间
        
        data格式:
        {
            "debate_id": "辩论ID"
        }
        """
        try:
            from app.services.debate_engine import get_debate_engine
            
            debate_id_str = data.get("debate_id")
            if not debate_id_str:
                await sio.emit("error", {"message": "debate_id is required"}, room=sid)
                return
            
            debate_id = ObjectId(debate_id_str)
            
            debate_engine = get_debate_engine()
            result = await debate_engine.join_debate(debate_id, sid)
            
            if "error" in result:
                await sio.emit("error", {"message": result["error"]}, room=sid)
                return
            
            await sio.enter_room(sid, debate_id_str)
            
            debate = result.get("debate", {})
            messages = result.get("messages", [])
            viewer_count = result.get("viewer_count", 0)
            
            await sio.emit(
                "joined_debate",
                {
                    "debate_id": debate_id_str,
                    "debate": _make_serializable(debate),
                    "messages": _make_serializable(messages),
                    "viewer_count": viewer_count
                },
                room=sid
            )
            
            await sio.emit(
                "user_joined",
                {"sid": sid, "viewer_count": viewer_count},
                room=debate_id_str,
                skip_sid=sid
            )
            
            logger.info(f"Client {sid} joined debate {debate_id_str}, viewer count: {viewer_count}")
            
        except Exception as e:
            logger.error(f"Error joining debate: {e}")
            await sio.emit("error", {"message": str(e)}, room=sid)
    
    @sio.event
    async def leave_debate(sid, data):
        """
        离开辩论直播间
        
        data格式:
        {
            "debate_id": "辩论ID"
        }
        """
        try:
            from app.services.debate_engine import get_debate_engine
            
            debate_id_str = data.get("debate_id")
            if not debate_id_str:
                await sio.emit("error", {"message": "debate_id is required"}, room=sid)
                return
            
            debate_id = ObjectId(debate_id_str)
            
            debate_engine = get_debate_engine()
            await debate_engine.leave_debate(debate_id, sid)
            
            socket_manager = get_socket_manager()
            viewer_count = socket_manager.get_debate_viewers(debate_id_str)
            
            await sio.leave_room(sid, debate_id_str)
            
            await sio.emit(
                "left_debate",
                {"debate_id": debate_id_str, "viewer_count": viewer_count},
                room=sid
            )
            
            await sio.emit(
                "user_left",
                {"sid": sid, "viewer_count": viewer_count},
                room=debate_id_str,
                skip_sid=sid
            )
            
            logger.info(f"Client {sid} left debate {debate_id_str}, viewer count: {viewer_count}")
            
        except Exception as e:
            logger.error(f"Error leaving debate: {e}")
            await sio.emit("error", {"message": str(e)}, room=sid)
    
    @sio.event
    async def send_danmaku(sid, data):
        """
        发送弹幕
        
        data格式:
        {
            "debate_id": "辩论ID",
            "content": "弹幕内容",
            "user_id": "用户ID（可选）",
            "user_name": "用户名（可选）",
            "color": "#ffffff（可选）",
            "position": "top/middle/bottom（可选）"
        }
        """
        try:
            debate_id_str = data.get("debate_id")
            content = data.get("content", "").strip()
            
            if not debate_id_str or not content:
                await sio.emit("error", {"message": "debate_id and content are required"}, room=sid)
                return
            
            # 限制弹幕长度
            if len(content) > 100:
                content = content[:100]
            
            debate_id = ObjectId(debate_id_str)
            
            # 准备弹幕数据
            danmaku_data = {
                "debate_id": debate_id,
                "content": content,
                "message_type": "danmaku",
                "created_at": datetime.utcnow(),
                "timestamp": datetime.utcnow().timestamp(),
                "user_id": data.get("user_id"),
                "user_name": data.get("user_name", "匿名用户"),
                "color": data.get("color", "#ffffff"),
                "position": data.get("position", "top")
            }
            
            # 保存到数据库
            db = get_database()
            await db.messages.insert_one(danmaku_data)
            
            # 转换为可序列化格式
            serializable_danmaku = _make_serializable(danmaku_data)
            
            # 广播给房间内所有用户
            await sio.emit(
                "new_danmaku",
                serializable_danmaku,
                room=debate_id_str
            )
            
            # 发送发送确认
            await sio.emit(
                "danmaku_sent",
                {"success": True, "danmaku": serializable_danmaku},
                room=sid
            )
            
        except Exception as e:
            print(f"Error sending danmaku: {e}")
            await sio.emit("error", {"message": str(e)}, room=sid)
    
    @sio.event
    async def get_recent_messages(sid, data):
        """
        获取最近的消息历史
        
        data格式:
        {
            "debate_id": "辩论ID",
            "limit": 50（可选，默认50）
        }
        """
        try:
            debate_id_str = data.get("debate_id")
            limit = data.get("limit", 50)
            
            if not debate_id_str:
                await sio.emit("error", {"message": "debate_id is required"}, room=sid)
                return
            
            debate_id = ObjectId(debate_id_str)
            
            # 查询最近的消息
            db = get_database()
            cursor = db.messages.find(
                {"debate_id": debate_id}
            ).sort("created_at", -1).limit(limit)
            
            messages = await cursor.to_list(length=limit)
            messages.reverse()  # 按时间正序排列
            
            await sio.emit(
                "recent_messages",
                {"debate_id": debate_id_str, "messages": _make_serializable(messages)},
                room=sid
            )
            
        except Exception as e:
            print(f"Error getting recent messages: {e}")
            await sio.emit("error", {"message": str(e)}, room=sid)
    
    @sio.event
    async def ping(sid, data):
        """心跳检测"""
        await sio.emit("pong", {"timestamp": datetime.utcnow().isoformat()}, room=sid)
    
    @sio.event
    async def join_arena(sid, data):
        """
        加入竞技场房间
        
        data格式:
        {
            "room_id": "房间ID"
        }
        """
        try:
            from app.services.arena_service import get_arena_service
            
            room_id = data.get("room_id")
            if not room_id:
                await sio.emit("error", {"message": "room_id is required"}, room=sid)
                return
            
            arena_service = get_arena_service()
            room = await arena_service.join_room(room_id, sid)
            
            if not room:
                await sio.emit("error", {"message": "Room not found"}, room=sid)
                return
            
            await sio.enter_room(sid, room_id)
            
            viewer_count = room.viewer_count
            
            await sio.emit(
                "joined_arena",
                {
                    "room_id": room_id,
                    "sid": sid,
                    "viewer_count": viewer_count
                },
                room=sid
            )
            
            await sio.emit(
                "user_joined_arena",
                {"sid": sid, "room_id": room_id, "viewer_count": viewer_count},
                room=room_id,
                skip_sid=sid
            )
            
            logger.info(f"Client {sid} joined arena room {room_id}, viewer count: {viewer_count}")
            
        except Exception as e:
            logger.error(f"Error joining arena: {e}")
            await sio.emit("error", {"message": str(e)}, room=sid)
    
    @sio.event
    async def leave_arena(sid, data):
        """
        离开竞技场房间
        
        data格式:
        {
            "room_id": "房间ID"
        }
        """
        try:
            from app.services.arena_service import get_arena_service
            from app.socket.manager import get_socket_manager
            
            room_id = data.get("room_id")
            if not room_id:
                await sio.emit("error", {"message": "room_id is required"}, room=sid)
                return
            
            arena_service = get_arena_service()
            await arena_service.leave_room(room_id, sid)
            
            socket_manager = get_socket_manager()
            viewer_count = socket_manager.get_arena_viewers(room_id)
            
            await sio.leave_room(sid, room_id)
            
            await sio.emit(
                "left_arena",
                {"room_id": room_id, "viewer_count": viewer_count},
                room=sid
            )
            
            await sio.emit(
                "user_left_arena",
                {"sid": sid, "room_id": room_id, "viewer_count": viewer_count},
                room=room_id,
                skip_sid=sid
            )
            
            logger.info(f"Client {sid} left arena room {room_id}, viewer count: {viewer_count}")
            
        except Exception as e:
            logger.error(f"Error leaving arena: {e}")
            await sio.emit("error", {"message": str(e)}, room=sid)
