from datetime import datetime
from typing import Dict, Optional
from bson import ObjectId
import socketio
from app.database import get_database
from app.services.debate_engine import get_debate_engine
from app.models.message import DanmakuCreate


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
        print(f"Client disconnected: {sid}")
        
        # 从所有房间中移除
        rooms = sio.rooms(sid)
        for room in rooms:
            if room != sid:  # 不包括默认的个人房间
                await sio.leave_room(sid, room)
                
                # 通知房间内其他用户有人离开
                await sio.emit(
                    "user_left",
                    {"sid": sid},
                    room=room
                )
    
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
            debate_id_str = data.get("debate_id")
            if not debate_id_str:
                await sio.emit("error", {"message": "debate_id is required"}, room=sid)
                return
            
            debate_id = ObjectId(debate_id_str)
            
            # 调用辩论引擎处理加入逻辑
            debate_engine = get_debate_engine()
            result = await debate_engine.join_debate(debate_id, sid)
            
            if "error" in result:
                await sio.emit("error", {"message": result["error"]}, room=sid)
                return
            
            # 加入Socket.IO房间
            await sio.enter_room(sid, debate_id_str)
            
            # 获取辩论信息
            debate = result.get("debate", {})
            messages = result.get("messages", [])
            viewer_count = result.get("viewer_count", 0)
            
            # 发送加入成功确认
            await sio.emit(
                "joined_debate",
                {
                    "debate_id": debate_id_str,
                    "debate": debate,
                    "messages": messages,
                    "viewer_count": viewer_count
                },
                room=sid
            )
            
            # 通知房间内其他用户有新观众加入
            await sio.emit(
                "user_joined",
                {"sid": sid, "viewer_count": viewer_count},
                room=debate_id_str,
                skip_sid=sid
            )
            
            print(f"Client {sid} joined debate {debate_id_str}")
            
        except Exception as e:
            print(f"Error joining debate: {e}")
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
            debate_id_str = data.get("debate_id")
            if not debate_id_str:
                await sio.emit("error", {"message": "debate_id is required"}, room=sid)
                return
            
            debate_id = ObjectId(debate_id_str)
            
            # 调用辩论引擎处理离开逻辑
            debate_engine = get_debate_engine()
            await debate_engine.leave_debate(debate_id, sid)
            
            # 离开Socket.IO房间
            await sio.leave_room(sid, debate_id_str)
            
            # 发送离开确认
            await sio.emit(
                "left_debate",
                {"debate_id": debate_id_str},
                room=sid
            )
            
            # 通知房间内其他用户有观众离开
            await sio.emit(
                "user_left",
                {"sid": sid},
                room=debate_id_str,
                skip_sid=sid
            )
            
            print(f"Client {sid} left debate {debate_id_str}")
            
        except Exception as e:
            print(f"Error leaving debate: {e}")
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
            danmaku_data["_id"] = str(danmaku_data["_id"])
            danmaku_data["debate_id"] = str(danmaku_data["debate_id"])
            
            # 广播给房间内所有用户
            await sio.emit(
                "new_danmaku",
                danmaku_data,
                room=debate_id_str
            )
            
            # 发送发送确认
            await sio.emit(
                "danmaku_sent",
                {"success": True, "danmaku": danmaku_data},
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
            
            # 转换为可序列化格式
            for msg in messages:
                msg["_id"] = str(msg["_id"])
                msg["debate_id"] = str(msg["debate_id"])
            
            await sio.emit(
                "recent_messages",
                {"debate_id": debate_id_str, "messages": messages},
                room=sid
            )
            
        except Exception as e:
            print(f"Error getting recent messages: {e}")
            await sio.emit("error", {"message": str(e)}, room=sid)
    
    @sio.event
    async def ping(sid, data):
        """心跳检测"""
        await sio.emit("pong", {"timestamp": datetime.utcnow().isoformat()}, room=sid)
