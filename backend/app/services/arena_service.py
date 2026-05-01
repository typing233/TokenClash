import asyncio
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId

from app.database import get_database
from app.models.arena import (
    ArenaRoom, ArenaParticipant, ArenaSkillCard, ArenaSkillType, 
    ArenaStage, ArenaJudgementResult, CreateRoomRequest
)
from app.services.dna_service import get_dna_service
from app.config import get_settings
from app.socket.manager import get_socket_manager
from app.socket_instance import sio
import logging

logger = logging.getLogger(__name__)

settings = get_settings()
dna_service = get_dna_service()


DEFAULT_SKILLS = [
    ArenaSkillCard(
        skill_id="lightning",
        name="雷击",
        description="对目标造成20点能量伤害",
        skill_type=ArenaSkillType.LIGHTNING,
        cost=15,
        effect_amount=20,
        icon="zap",
        color="#ff6b6b"
    ),
    ArenaSkillCard(
        skill_id="shield",
        name="护盾",
        description="为目标添加护盾，持续10秒内免疫伤害",
        skill_type=ArenaSkillType.SHIELD,
        cost=20,
        duration=10,
        icon="shield",
        color="#4ecdc4"
    ),
    ArenaSkillCard(
        skill_id="energy_boost",
        name="能量充能",
        description="为目标恢复30点能量",
        skill_type=ArenaSkillType.ENERGY_BOOST,
        cost=10,
        effect_amount=30,
        icon="activity",
        color="#ffe66d"
    ),
    ArenaSkillCard(
        skill_id="vote_multiplier",
        name="投票增幅",
        description="目标获得的票数在10秒内变为2倍",
        skill_type=ArenaSkillType.VOTE_MULTIPLIER,
        cost=25,
        duration=10,
        effect_amount=2.0,
        icon="trending-up",
        color="#a78bfa"
    ),
    ArenaSkillCard(
        skill_id="freeze",
        name="冰冻",
        description="冻结目标5秒，期间无法获得能量和投票",
        skill_type=ArenaSkillType.FREEZE,
        cost=20,
        duration=5,
        icon="snowflake",
        color="#74b9ff"
    ),
    ArenaSkillCard(
        skill_id="heal",
        name="治愈",
        description="恢复目标到满能量",
        skill_type=ArenaSkillType.HEAL,
        cost=30,
        icon="heart",
        color="#fd79a8"
    ),
]


class ArenaService:
    """竞技场核心服务"""
    
    def __init__(self):
        self.db = None
        self.active_rooms: Dict[str, 'ArenaSession'] = {}
        self.room_tasks: Dict[str, asyncio.Task] = {}
    
    def get_db(self):
        """获取数据库实例"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    def get_default_skills(self) -> List[ArenaSkillCard]:
        """获取默认技能列表"""
        return DEFAULT_SKILLS
    
    async def create_room(
        self,
        request: CreateRoomRequest,
        model_configs: Dict
    ) -> ArenaRoom:
        """创建新的竞技场房间"""
        db = self.get_db()
        
        room_id = f"arena_{uuid.uuid4().hex[:12]}"
        
        model1 = model_configs.get(request.model1_id) or {}
        model2 = model_configs.get(request.model2_id) or {}
        
        participants = [
            ArenaParticipant(
                model_id=request.model1_id,
                model_name=model1.get("model_name", request.model1_id),
                display_name=model1.get("display_name", request.model1_id),
                side="affirmative",
                energy=100,
                max_energy=100,
                votes=0
            ),
            ArenaParticipant(
                model_id=request.model2_id,
                model_name=model2.get("model_name", request.model2_id),
                display_name=model2.get("display_name", request.model2_id),
                side="negative",
                energy=100,
                max_energy=100,
                votes=0
            )
        ]
        
        room = ArenaRoom(
            room_id=room_id,
            title=request.title,
            topic=request.topic,
            stage=ArenaStage.WAITING,
            current_round=0,
            participants=participants,
            viewer_count=0,
            countdown_remaining=request.countdown_duration,
            total_countdown=request.countdown_duration,
            available_skills=self.get_default_skills(),
            is_active=True
        )
        
        room_dict = {
            **room.to_dict(),
            "participants": [p.model_dump() for p in participants],
            "available_skills": [s.model_dump() for s in room.available_skills],
        }
        
        await db.arena_rooms.insert_one(room_dict)
        
        session = ArenaSession(room_id, self)
        self.active_rooms[room_id] = session
        
        return room
    
    async def get_room(self, room_id: str) -> Optional[ArenaRoom]:
        """获取房间信息"""
        db = self.get_db()
        
        room_doc = await db.arena_rooms.find_one({"room_id": room_id})
        if not room_doc:
            return None
        
        return self._doc_to_room(room_doc)
    
    def _doc_to_room(self, doc: Dict) -> ArenaRoom:
        """将数据库文档转换为房间对象"""
        participants = [
            ArenaParticipant(**p) for p in doc.get("participants", [])
        ]
        
        stage = doc.get("stage", "waiting")
        if isinstance(stage, str):
            try:
                stage = ArenaStage(stage)
            except ValueError:
                stage = ArenaStage.WAITING
        
        return ArenaRoom(
            room_id=doc["room_id"],
            title=doc["title"],
            topic=doc.get("topic", ""),
            category=doc.get("category", "general"),
            stage=stage,
            current_round=doc.get("current_round", 0),
            participants=participants,
            viewer_count=doc.get("viewer_count", 0),
            viewer_sids=doc.get("viewer_sids", []),
            countdown_remaining=doc.get("countdown_remaining", 60),
            total_countdown=doc.get("total_countdown", 60),
            created_at=doc.get("created_at"),
            started_at=doc.get("started_at"),
            finished_at=doc.get("finished_at"),
            winner=doc.get("winner"),
            winner_display_name=doc.get("winner_display_name"),
            final_scores=doc.get("final_scores", {}),
            used_skills=doc.get("used_skills", []),
            is_active=doc.get("is_active", True)
        )
    
    async def get_active_rooms(self) -> List[ArenaRoom]:
        """获取所有活跃房间"""
        db = self.get_db()
        
        cursor = db.arena_rooms.find(
            {"is_active": True, "stage": {"$ne": ArenaStage.FINISHED.value}}
        ).sort("created_at", -1).limit(20)
        
        rooms = []
        async for doc in cursor:
            rooms.append(self._doc_to_room(doc))
        
        return rooms
    
    async def join_room(self, room_id: str, user_sid: str) -> Optional[ArenaRoom]:
        """用户加入房间"""
        db = self.get_db()
        socket_manager = get_socket_manager()
        
        viewer_count = socket_manager.join_arena_room(user_sid, room_id)
        
        result = await db.arena_rooms.update_one(
            {"room_id": room_id},
            {
                "$set": {"viewer_count": viewer_count},
                "$addToSet": {"viewer_sids": user_sid}
            }
        )
        
        if result.modified_count == 0:
            room = await self.get_room(room_id)
            if not room:
                return None
        
        logger.info(f"User {user_sid} joined arena room {room_id}, viewer count: {viewer_count}")
        
        return await self.get_room(room_id)
    
    async def leave_room(self, room_id: str, user_sid: str):
        """用户离开房间"""
        socket_manager = get_socket_manager()
        
        result = await socket_manager.leave_arena_room(user_sid)
        
        if result:
            new_count = result.get("viewer_count", 0)
            db = self.get_db()
            await db.arena_rooms.update_one(
                {"room_id": room_id},
                {
                    "$set": {"viewer_count": new_count},
                    "$pull": {"viewer_sids": user_sid}
                }
            )
            logger.info(f"User {user_sid} left arena room {room_id}, viewer count: {new_count}")
    
    async def start_room(self, room_id: str) -> bool:
        """开始房间倒计时"""
        db = self.get_db()
        
        room = await self.get_room(room_id)
        if not room:
            return False
        
        await db.arena_rooms.update_one(
            {"room_id": room_id},
            {
                "$set": {
                    "stage": ArenaStage.ACTIVE.value,
                    "started_at": datetime.utcnow()
                }
            }
        )
        
        if room_id in self.active_rooms:
            session = self.active_rooms[room_id]
            task = asyncio.create_task(session.run_arena())
            self.room_tasks[room_id] = task
        
        return True
    
    async def use_skill(
        self,
        room_id: str,
        skill_id: str,
        target_model_id: str,
        user_sid: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用技能"""
        db = self.get_db()
        
        room = await self.get_room(room_id)
        if not room:
            return {"success": False, "error": "Room not found"}
        
        if room.stage not in [ArenaStage.ACTIVE, ArenaStage.VOTING]:
            return {"success": False, "error": "Room not in active stage"}
        
        skill = next((s for s in room.available_skills if s.skill_id == skill_id), None)
        if not skill:
            return {"success": False, "error": "Skill not found"}
        
        target = next((p for p in room.participants if p.model_id == target_model_id), None)
        if not target:
            return {"success": False, "error": "Target not found"}
        
        now = datetime.utcnow()
        effect_applied = False
        effect_message = ""
        
        if skill.skill_type == ArenaSkillType.LIGHTNING:
            if not (target.shield_active and target.shield_ends_at and target.shield_ends_at > now):
                damage = int(skill.effect_amount)
                target.energy = max(0, target.energy - damage)
                effect_message = f"对 {target.display_name} 造成了 {damage} 点伤害！"
                effect_applied = True
            else:
                effect_message = f"{target.display_name} 的护盾抵挡了攻击！"
        
        elif skill.skill_type == ArenaSkillType.SHIELD:
            target.shield_active = True
            target.shield_ends_at = now + timedelta(seconds=skill.duration)
            effect_message = f"{target.display_name} 获得了护盾保护！"
            effect_applied = True
        
        elif skill.skill_type == ArenaSkillType.ENERGY_BOOST:
            if not (target.is_frozen and target.frozen_until and target.frozen_until > now):
                boost = int(skill.effect_amount)
                target.energy = min(target.max_energy, target.energy + boost)
                effect_message = f"{target.display_name} 恢复了 {boost} 点能量！"
                effect_applied = True
            else:
                effect_message = f"{target.display_name} 被冻结了！"
        
        elif skill.skill_type == ArenaSkillType.VOTE_MULTIPLIER:
            target.has_vote_multiplier = True
            target.vote_multiplier_ends_at = now + timedelta(seconds=skill.duration)
            effect_message = f"{target.display_name} 的投票倍数已激活！"
            effect_applied = True
        
        elif skill.skill_type == ArenaSkillType.FREEZE:
            target.is_frozen = True
            target.frozen_until = now + timedelta(seconds=skill.duration)
            effect_message = f"{target.display_name} 被冻结了 {skill.duration} 秒！"
            effect_applied = True
        
        elif skill.skill_type == ArenaSkillType.HEAL:
            target.energy = target.max_energy
            effect_message = f"{target.display_name} 的能量已恢复到满！"
            effect_applied = True
        
        used_skill = {
            "skill_id": skill_id,
            "skill_name": skill.name,
            "target_model_id": target_model_id,
            "target_display_name": target.display_name,
            "effect_message": effect_message,
            "effect_applied": effect_applied,
            "user_sid": user_sid,
            "timestamp": now,
        }
        
        await db.arena_rooms.update_one(
            {"room_id": room_id},
            {
                "$set": {
                    "participants": [p.model_dump() for p in room.participants]
                },
                "$push": {"used_skills": used_skill}
            }
        )
        
        await sio.emit(
            "skill_used",
            used_skill,
            room=room_id
        )
        
        return {
            "success": True,
            "effect_applied": effect_applied,
            "message": effect_message,
            "room": room.to_dict()
        }
    
    async def cast_vote(
        self,
        room_id: str,
        model_id: str,
        user_sid: Optional[str] = None
    ) -> Dict[str, Any]:
        """投票"""
        db = self.get_db()
        
        room = await self.get_room(room_id)
        if not room:
            return {"success": False, "error": "Room not found"}
        
        if room.stage not in [ArenaStage.ACTIVE, ArenaStage.VOTING]:
            return {"success": False, "error": "Room not in active or voting stage"}
        
        target = next((p for p in room.participants if p.model_id == model_id), None)
        if not target:
            return {"success": False, "error": "Target not found"}
        
        now = datetime.utcnow()
        
        if target.is_frozen and target.frozen_until and target.frozen_until > now:
            return {"success": False, "error": "Target is frozen"}
        
        vote_count = 1
        if target.has_vote_multiplier and target.vote_multiplier_ends_at and target.vote_multiplier_ends_at > now:
            vote_count = 2
        
        target.votes += vote_count
        
        await db.arena_rooms.update_one(
            {"room_id": room_id},
            {
                "$set": {
                    "participants": [p.model_dump() for p in room.participants]
                }
            }
        )
        
        await sio.emit(
            "vote_cast",
            {
                "model_id": model_id,
                "display_name": target.display_name,
                "votes": target.votes,
                "multiplied": vote_count > 1
            },
            room=room_id
        )
        
        return {
            "success": True,
            "model_id": model_id,
            "votes": target.votes,
            "multiplier_applied": vote_count > 1
        }
    
    async def add_energy(
        self,
        room_id: str,
        model_id: str,
        amount: int = 10
    ) -> Dict[str, Any]:
        """充能量"""
        db = self.get_db()
        
        room = await self.get_room(room_id)
        if not room:
            return {"success": False, "error": "Room not found"}
        
        if room.stage not in [ArenaStage.ACTIVE, ArenaStage.VOTING]:
            return {"success": False, "error": "Room not in active stage"}
        
        target = next((p for p in room.participants if p.model_id == model_id), None)
        if not target:
            return {"success": False, "error": "Target not found"}
        
        now = datetime.utcnow()
        if target.is_frozen and target.frozen_until and target.frozen_until > now:
            return {"success": False, "error": "Target is frozen"}
        
        new_energy = min(target.max_energy, target.energy + amount)
        actual_added = new_energy - target.energy
        target.energy = new_energy
        
        await db.arena_rooms.update_one(
            {"room_id": room_id},
            {
                "$set": {
                    "participants": [p.model_dump() for p in room.participants]
                }
            }
        )
        
        await sio.emit(
            "energy_updated",
            {
                "model_id": model_id,
                "display_name": target.display_name,
                "energy": target.energy,
                "max_energy": target.max_energy,
                "added": actual_added
            },
            room=room_id
        )
        
        return {
            "success": True,
            "model_id": model_id,
            "energy": target.energy,
            "added": actual_added
        }
    
    async def judge_winner(self, room_id: str) -> Optional[ArenaJudgementResult]:
        """AI裁判判定胜负"""
        db = self.get_db()
        
        room = await self.get_room(room_id)
        if not room:
            return None
        
        if len(room.participants) < 2:
            return None
        
        p1, p2 = room.participants[0], room.participants[1]
        
        max_possible_energy = 100
        p1_energy_score = p1.energy / max_possible_energy
        p2_energy_score = p2.energy / max_possible_energy
        
        total_votes = p1.votes + p2.votes
        if total_votes > 0:
            p1_vote_score = p1.votes / total_votes
            p2_vote_score = p2.votes / total_votes
        else:
            p1_vote_score = p2_vote_score = 0.5
        
        p1_dna_score = await self._calculate_dna_score(p1.model_id)
        p2_dna_score = await self._calculate_dna_score(p2.model_id)
        
        energy_weight = 0.3
        vote_weight = 0.4
        dna_weight = 0.3
        
        p1_total = (
            p1_energy_score * energy_weight +
            p1_vote_score * vote_weight +
            p1_dna_score * dna_weight
        )
        
        p2_total = (
            p2_energy_score * energy_weight +
            p2_vote_score * vote_weight +
            p2_dna_score * dna_weight
        )
        
        if p1_total > p2_total:
            winner = p1
            loser = p2
        elif p2_total > p1_total:
            winner = p2
            loser = p1
        else:
            if p1.votes > p2.votes:
                winner = p1
                loser = p2
            else:
                winner = p2
                loser = p1
        
        result = ArenaJudgementResult(
            winner_model_id=winner.model_id,
            winner_display_name=winner.display_name,
            total_score=max(p1_total, p2_total),
            energy_score=p1_energy_score if winner == p1 else p2_energy_score,
            vote_score=p1_vote_score if winner == p1 else p2_vote_score,
            dna_score=p1_dna_score if winner == p1 else p2_dna_score,
            details={
                "p1": {
                    "model_id": p1.model_id,
                    "display_name": p1.display_name,
                    "energy": p1.energy,
                    "votes": p1.votes,
                    "scores": {
                        "energy": p1_energy_score,
                        "vote": p1_vote_score,
                        "dna": p1_dna_score,
                        "total": p1_total
                    }
                },
                "p2": {
                    "model_id": p2.model_id,
                    "display_name": p2.display_name,
                    "energy": p2.energy,
                    "votes": p2.votes,
                    "scores": {
                        "energy": p2_energy_score,
                        "vote": p2_vote_score,
                        "dna": p2_dna_score,
                        "total": p2_total
                    }
                }
            }
        )
        
        await db.arena_rooms.update_one(
            {"room_id": room_id},
            {
                "$set": {
                    "stage": ArenaStage.FINISHED.value,
                    "winner": result.winner_model_id,
                    "winner_display_name": result.winner_display_name,
                    "final_scores": result.details,
                    "finished_at": datetime.utcnow(),
                    "is_active": False
                }
            }
        )
        
        await dna_service.update_fingerprint(
            model_id=winner.model_id,
            model_name=winner.model_name,
            display_name=winner.display_name,
            messages=winner.messages,
            is_winner=True
        )
        
        await dna_service.update_fingerprint(
            model_id=loser.model_id,
            model_name=loser.model_name,
            display_name=loser.display_name,
            messages=loser.messages,
            is_winner=False
        )
        
        return result
    
    async def _calculate_dna_score(self, model_id: str) -> float:
        """基于DNA指纹计算分数"""
        fingerprint = await dna_service.get_fingerprint(model_id)
        
        if not fingerprint:
            return 0.5
        
        win_rate = 0.5
        if fingerprint.debate_participations > 0:
            win_rate = fingerprint.wins / fingerprint.debate_participations
        
        diversity_score = (
            fingerprint.context_entropy / 8.0 +
            fingerprint.semantic_diversity +
            fingerprint.vocabulary_richness
        ) / 3.0
        
        consistency_bonus = fingerprint.response_consistency * 0.3
        
        score = (
            win_rate * 0.4 +
            diversity_score * 0.4 +
            consistency_bonus * 0.2
        )
        
        return max(0.0, min(1.0, score))


class ArenaSession:
    """单个竞技场房间的会话管理"""
    
    def __init__(self, room_id: str, service: ArenaService):
        self.room_id = room_id
        self.service = service
        self.db = get_database()
    
    async def run_arena(self):
        """运行竞技场流程"""
        try:
            room = await self.service.get_room(self.room_id)
            if not room:
                return
            
            countdown = room.total_countdown
            
            while countdown > 0:
                await asyncio.sleep(1)
                countdown -= 1
                
                await self.db.arena_rooms.update_one(
                    {"room_id": self.room_id},
                    {"$set": {"countdown_remaining": countdown}}
                )
                
                await sio.emit(
                    "countdown_update",
                    {
                        "room_id": self.room_id,
                        "countdown_remaining": countdown,
                        "total_countdown": room.total_countdown
                    },
                    room=self.room_id
                )
            
            await self.db.arena_rooms.update_one(
                {"room_id": self.room_id},
                {"$set": {"stage": ArenaStage.VOTING.value}}
            )
            
            await sio.emit(
                "stage_change",
                {
                    "room_id": self.room_id,
                    "stage": ArenaStage.VOTING.value,
                    "message": "倒计时结束！进入最终投票阶段。"
                },
                room=self.room_id
            )
            
            await asyncio.sleep(10)
            
            await self.db.arena_rooms.update_one(
                {"room_id": self.room_id},
                {"$set": {"stage": ArenaStage.JUDGING.value}}
            )
            
            await sio.emit(
                "stage_change",
                {
                    "room_id": self.room_id,
                    "stage": ArenaStage.JUDGING.value,
                    "message": "投票结束！AI裁判正在判定胜负..."
                },
                room=self.room_id
            )
            
            result = await self.service.judge_winner(self.room_id)
            
            if result:
                await sio.emit(
                    "arena_result",
                    {
                        "room_id": self.room_id,
                        "winner_model_id": result.winner_model_id,
                        "winner_display_name": result.winner_display_name,
                        "total_score": result.total_score,
                        "energy_score": result.energy_score,
                        "vote_score": result.vote_score,
                        "dna_score": result.dna_score,
                        "details": result.details,
                        "stage": ArenaStage.FINISHED.value
                    },
                    room=self.room_id
                )
        
        except Exception as e:
            print(f"Arena session error: {e}")
            await self.db.arena_rooms.update_one(
                {"room_id": self.room_id},
                {"$set": {"is_active": False, "stage": ArenaStage.FINISHED.value}}
            )
        
        finally:
            if self.room_id in self.service.active_rooms:
                del self.service.active_rooms[self.room_id]
            if self.room_id in self.service.room_tasks:
                del self.service.room_tasks[self.room_id]


arena_service = ArenaService()


def get_arena_service() -> ArenaService:
    """获取竞技场服务实例"""
    return arena_service
