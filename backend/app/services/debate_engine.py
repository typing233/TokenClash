import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any
from bson import ObjectId
from app.database import get_database
from app.models.debate import DebateStage, Debate, DebateUpdate
from app.models.message import Message, ModelMessage, SystemMessage
from app.services.volcano_api import get_volcano_client
from app.config import get_settings
import socketio


def _make_serializable(obj):
    """将包含ObjectId/datetime的字典转换为JSON可序列化格式"""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


settings = get_settings()
volcano_client = get_volcano_client()


class DebateEngine:
    """辩论引擎 - 管理辩论的整个生命周期"""
    
    def __init__(self):
        self.active_debates: Dict[str, 'DebateSession'] = {}
        self.db = None
    
    def get_db(self):
        """获取数据库实例"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    async def create_debate(
        self,
        topic_id: ObjectId,
        title: str,
        participants: List[Dict],
        max_rounds: int = 5,
        category: str = "general"
    ) -> Debate:
        """
        创建新的辩论
        
        Args:
            topic_id: 话题ID
            title: 辩论标题
            participants: 参与者列表 [{"model_id": ..., "model_name": ..., "display_name": ..., "side": ...}]
            max_rounds: 最大轮次
            category: 分类
        
        Returns:
            创建的辩论对象
        """
        db = self.get_db()
        
        # 准备辩论数据
        debate_data = {
            "topic_id": topic_id,
            "title": title,
            "participants": participants,
            "max_rounds": max_rounds,
            "category": category,
            "stage": "waiting",
            "current_round": 0,
            "current_speaker": None,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "finished_at": None,
            "viewer_count": 0,
            "message_count": 0,
            "is_active": True,
            "vote_results": None
        }
        
        # 插入数据库
        result = await db.debates.insert_one(debate_data)
        debate_data["_id"] = result.inserted_id
        
        # 更新话题的辩论计数
        await db.topics.update_one(
            {"_id": topic_id},
            {"$inc": {"debate_count": 1}, "$set": {"updated_at": datetime.utcnow()}}
        )
        
        return Debate(**debate_data)
    
    async def start_debate(self, debate_id: ObjectId, sio: socketio.AsyncServer) -> bool:
        """
        开始辩论
        
        Args:
            debate_id: 辩论ID
            sio: Socket.IO服务器实例
        
        Returns:
            是否成功开始
        """
        db = self.get_db()
        
        # 获取辩论信息
        debate_doc = await db.debates.find_one({"_id": debate_id})
        if not debate_doc:
            return False
        
        debate = Debate(**debate_doc)
        
        # 更新辩论状态
        await db.debates.update_one(
            {"_id": debate_id},
            {
                "$set": {
                    "stage": "opening",
                    "current_round": 1,
                    "started_at": datetime.utcnow()
                }
            }
        )
        
        # 创建辩论会话
        session = DebateSession(debate_id, sio)
        self.active_debates[str(debate_id)] = session
        
        # 发送系统消息：辩论开始
        await self._send_system_message(
            debate_id=debate_id,
            event_type="debate_start",
            content="辩论开始！首先进入开篇陈词阶段。",
            metadata={"stage": "opening", "round": 1}
        )
        
        # 启动辩论流程
        asyncio.create_task(session.run_debate(debate))
        
        return True
    
    async def join_debate(self, debate_id: ObjectId, user_sid: str) -> Dict:
        """
        用户加入辩论直播间
        
        Args:
            debate_id: 辩论ID
            user_sid: 用户的Socket.IO SID
        
        Returns:
            辩论当前状态
        """
        db = self.get_db()
        
        # 增加观众计数
        await db.debates.update_one(
            {"_id": debate_id},
            {"$inc": {"viewer_count": 1}}
        )
        
        # 获取辩论当前状态
        debate_doc = await db.debates.find_one({"_id": debate_id})
        if not debate_doc:
            return {"error": "Debate not found"}
        
        # 获取最近的消息
        messages = await db.messages.find(
            {"debate_id": debate_id}
        ).sort("created_at", 1).limit(50).to_list(length=50)
        
        return {
            "debate": debate_doc,
            "messages": messages,
            "viewer_count": debate_doc.get("viewer_count", 0)
        }
    
    async def leave_debate(self, debate_id: ObjectId, user_sid: str):
        """
        用户离开辩论直播间
        
        Args:
            debate_id: 辩论ID
            user_sid: 用户的Socket.IO SID
        """
        db = self.get_db()
        
        # 减少观众计数（不低于0）
        await db.debates.update_one(
            {"_id": debate_id, "viewer_count": {"$gt": 0}},
            {"$inc": {"viewer_count": -1}}
        )
    
    async def _send_system_message(
        self,
        debate_id: ObjectId,
        event_type: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """发送系统消息"""
        db = self.get_db()
        
        message_data = {
            "debate_id": debate_id,
            "content": content,
            "message_type": "system",
            "created_at": datetime.utcnow(),
            "timestamp": datetime.utcnow().timestamp(),
            "event_type": event_type,
            "metadata": metadata or {}
        }
        
        await db.messages.insert_one(message_data)


class DebateSession:
    """单个辩论的会话管理"""
    
    def __init__(self, debate_id: ObjectId, sio: socketio.AsyncServer):
        self.debate_id = debate_id
        self.sio = sio
        self.db = get_database()
        self.context_messages: List[Dict] = []  # 对话上下文
    
    async def run_debate(self, debate: Debate):
        """运行完整的辩论流程"""
        try:
            # 1. 开篇陈词阶段
            await self._run_opening_stage(debate)
            
            # 2. 交叉反驳阶段
            await self._run_cross_examination_stage(debate)
            
            # 3. 总结陈词阶段
            await self._run_closing_stage(debate)
            
            # 4. 进入投票阶段
            await self._enter_voting_stage(debate)
            
        except Exception as e:
            print(f"辩论运行出错: {e}")
            await self._handle_debate_error(debate)
    
    async def _run_opening_stage(self, debate: Debate):
        """运行开篇陈词阶段"""
        await self._send_stage_change("opening", 1)
        
        # 正方先发言
        affirmative = [p for p in debate.participants if p["side"] == "affirmative"][0]
        negative = [p for p in debate.participants if p["side"] == "negative"][0]
        
        # 更新当前发言者
        await self._update_debate_state(current_speaker=affirmative["model_id"])
        
        # 正方开篇陈词
        await self._generate_and_broadcast_message(
            model=affirmative,
            topic=debate.title,
            stage="opening",
            round_number=1
        )
        
        # 等待2秒，模拟真实辩论的节奏
        await asyncio.sleep(2)
        
        # 更新当前发言者
        await self._update_debate_state(current_speaker=negative["model_id"])
        
        # 反方开篇陈词
        await self._generate_and_broadcast_message(
            model=negative,
            topic=debate.title,
            stage="opening",
            round_number=1
        )
        
        await asyncio.sleep(2)
    
    async def _run_cross_examination_stage(self, debate: Debate):
        """运行交叉反驳阶段"""
        await self._send_stage_change("cross_examination", 2)
        
        affirmative = [p for p in debate.participants if p["side"] == "affirmative"][0]
        negative = [p for p in debate.participants if p["side"] == "negative"][0]
        
        # 每轮交叉反驳：正方反驳 -> 反方反驳 -> 正方再反驳 -> 反方再反驳
        # 这里简化为2轮交叉反驳
        
        for round_num in range(1, 3):  # 2轮交叉反驳
            await self._update_debate_state(
                current_round=debate.current_round + round_num,
                current_speaker=affirmative["model_id"]
            )
            
            # 获取反方上一轮的论点用于反驳
            last_negative_arg = self._get_last_argument(negative["model_id"])
            
            # 正方反驳
            await self._generate_and_broadcast_message(
                model=affirmative,
                topic=debate.title,
                stage="cross_examination",
                round_number=round_num,
                opponent_argument=last_negative_arg
            )
            
            await asyncio.sleep(2)
            
            # 更新当前发言者
            await self._update_debate_state(current_speaker=negative["model_id"])
            
            # 获取正方上一轮的论点用于反驳
            last_affirmative_arg = self._get_last_argument(affirmative["model_id"])
            
            # 反方反驳
            await self._generate_and_broadcast_message(
                model=negative,
                topic=debate.title,
                stage="cross_examination",
                round_number=round_num,
                opponent_argument=last_affirmative_arg
            )
            
            await asyncio.sleep(2)
    
    async def _run_closing_stage(self, debate: Debate):
        """运行总结陈词阶段"""
        await self._send_stage_change("closing", debate.current_round + 1)
        
        affirmative = [p for p in debate.participants if p["side"] == "affirmative"][0]
        negative = [p for p in debate.participants if p["side"] == "negative"][0]
        
        # 更新当前发言者
        await self._update_debate_state(
            current_round=debate.current_round + 1,
            current_speaker=affirmative["model_id"]
        )
        
        # 正方总结陈词
        await self._generate_and_broadcast_message(
            model=affirmative,
            topic=debate.title,
            stage="closing",
            round_number=1
        )
        
        await asyncio.sleep(2)
        
        # 更新当前发言者
        await self._update_debate_state(current_speaker=negative["model_id"])
        
        # 反方总结陈词
        await self._generate_and_broadcast_message(
            model=negative,
            topic=debate.title,
            stage="closing",
            round_number=1
        )
        
        await asyncio.sleep(2)
    
    async def _enter_voting_stage(self, debate: Debate):
        """进入投票阶段"""
        await self._update_debate_state(
            stage="voting",
            current_speaker=None
        )
        
        await self._send_system_message(
            event_type="voting_start",
            content="辩论结束！现在进入投票阶段，请为您支持的辩手投票。",
            metadata={"stage": "voting"}
        )
        
        # 投票阶段持续60秒
        await asyncio.sleep(60)
        
        # 结束投票，计算结果
        await self._finish_debate(debate)
    
    async def _finish_debate(self, debate: Debate):
        """结束辩论，计算结果"""
        from app.services.ranking_service import get_ranking_service
        
        # 计算投票结果
        ranking_service = get_ranking_service()
        vote_result = await ranking_service.calculate_debate_result(self.debate_id)
        
        # 更新辩论状态
        await self._update_debate_state(
            stage="finished",
            finished_at=datetime.utcnow(),
            vote_results=vote_result.model_dump() if vote_result else None
        )
        
        # 发送系统消息
        winner_info = ""
        if vote_result and vote_result.winner_display_name:
            winner_info = f"获胜者是：{vote_result.winner_display_name}！"
        
        await self._send_system_message(
            event_type="debate_finish",
            content=f"投票结束！{winner_info}感谢参与！",
            metadata={
                "stage": "finished",
                "vote_results": vote_result.model_dump() if vote_result else None
            }
        )
        
        # 更新模型统计
        if vote_result:
            await ranking_service.update_model_stats_after_debate(
                debate_id=self.debate_id,
                vote_result=vote_result
            )
        
        # 从活跃辩论中移除
        debate_engine = get_debate_engine()
        if str(self.debate_id) in debate_engine.active_debates:
            del debate_engine.active_debates[str(self.debate_id)]
    
    async def _generate_and_broadcast_message(
        self,
        model: Dict,
        topic: str,
        stage: str,
        round_number: int,
        opponent_argument: Optional[str] = None
    ):
        """生成论点并广播消息"""
        try:
            # 调用模型生成论点
            content = await volcano_client.generate_argument(
                model_name=model["model_name"],
                topic=topic,
                side=model["side"],
                stage=stage,
                round_number=round_number,
                context_messages=self.context_messages,
                opponent_argument=opponent_argument
            )
            
            # 保存到上下文（包含model_id以便后续过滤）
            self.context_messages.append({
                "role": "assistant",
                "content": content,
                "model_id": model["model_id"]
            })
            
            # 准备消息数据
            message_data = {
                "debate_id": self.debate_id,
                "content": content,
                "message_type": "model",
                "created_at": datetime.utcnow(),
                "timestamp": datetime.utcnow().timestamp(),
                "model_id": model["model_id"],
                "model_name": model["model_name"],
                "display_name": model["display_name"],
                "side": model["side"],
                "round_number": round_number,
                "stage": stage
            }
            
            # 保存到数据库
            await self.db.messages.insert_one(message_data)
            
            # 更新辩论的消息计数
            await self.db.debates.update_one(
                {"_id": self.debate_id},
                {"$inc": {"message_count": 1}}
            )
            
            # 通过Socket.IO广播消息（转换为可序列化格式）
            await self.sio.emit(
                "new_message",
                _make_serializable(message_data),
                room=str(self.debate_id)
            )
            
            # 同时发送到实时流（模拟打字效果）
            await self._stream_message_content(model, content, stage, round_number)
            
        except Exception as e:
            print(f"生成论点出错: {e}")
            # 发送错误消息
            error_message = {
                "debate_id": self.debate_id,
                "content": f"抱歉，{model['display_name']}暂时无法发言。",
                "message_type": "system",
                "created_at": datetime.utcnow(),
                "timestamp": datetime.utcnow().timestamp(),
                "event_type": "model_error",
                "metadata": {"model_id": model["model_id"]}
            }
            await self.db.messages.insert_one(error_message)
            await self.sio.emit("new_message", _make_serializable(error_message), room=str(self.debate_id))
    
    async def _stream_message_content(
        self,
        model: Dict,
        content: str,
        stage: str,
        round_number: int
    ):
        """流式发送消息内容，模拟打字效果"""
        # 简单实现：每100ms发送一部分
        chunk_size = 50  # 每个chunk的字符数
        total_chars = len(content)
        
        for i in range(0, total_chars, chunk_size):
            chunk = content[i:i + chunk_size]
            
            stream_data = {
                "debate_id": str(self.debate_id),
                "model_id": model["model_id"],
                "display_name": model["display_name"],
                "side": model["side"],
                "content": chunk,
                "is_complete": i + chunk_size >= total_chars,
                "stage": stage,
                "round_number": round_number
            }
            
            await self.sio.emit(
                "message_stream",
                stream_data,
                room=str(self.debate_id)
            )
            
            # 等待一小段时间，模拟打字
            await asyncio.sleep(0.1)
    
    async def _update_debate_state(self, **kwargs):
        """更新辩论状态"""
        update_data = {"$set": kwargs}
        await self.db.debates.update_one({"_id": self.debate_id}, update_data)
        
        # 广播状态更新（转换为可序列化格式）
        await self.sio.emit(
            "debate_state_update",
            _make_serializable(kwargs),
            room=str(self.debate_id)
        )
    
    async def _send_stage_change(self, stage: str, round_number: int):
        """发送阶段变更消息"""
        stage_names = {
            "opening": "开篇陈词",
            "cross_examination": "交叉反驳",
            "closing": "总结陈词",
            "voting": "投票阶段",
            "finished": "辩论结束"
        }
        
        stage_name = stage_names.get(stage, stage)
        
        await self._send_system_message(
            event_type="stage_change",
            content=f"进入{stage_name}阶段",
            metadata={"stage": stage, "round": round_number}
        )
        
        await self._update_debate_state(stage=stage, current_round=round_number)
    
    async def _send_system_message(self, event_type: str, content: str, metadata: Optional[Dict] = None):
        """发送系统消息"""
        message_data = {
            "debate_id": self.debate_id,
            "content": content,
            "message_type": "system",
            "created_at": datetime.utcnow(),
            "timestamp": datetime.utcnow().timestamp(),
            "event_type": event_type,
            "metadata": metadata or {}
        }
        
        await self.db.messages.insert_one(message_data)
        await self.sio.emit("new_message", _make_serializable(message_data), room=str(self.debate_id))
    
    def _get_last_argument(self, model_id: str) -> Optional[str]:
        """获取指定模型的上一个论点"""
        for msg in reversed(self.context_messages):
            if msg.get("role") == "assistant" and msg.get("model_id") == model_id:
                return msg.get("content")
        return None
    
    async def _handle_debate_error(self, debate: Debate):
        """处理辩论错误"""
        await self._update_debate_state(
            stage="finished",
            finished_at=datetime.utcnow()
        )
        
        await self._send_system_message(
            event_type="debate_error",
            content="辩论出现错误，已提前结束。",
            metadata={"stage": "finished"}
        )


# 创建全局辩论引擎实例
debate_engine = DebateEngine()


def get_debate_engine() -> DebateEngine:
    """获取辩论引擎实例"""
    return debate_engine
