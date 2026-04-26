from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId
from app.database import get_database
from app.models.vote import VoteResult, Vote
from app.models.model_stats import ModelStats, RankingItem, OverallRanking, CategoryRanking
from app.config import get_settings


settings = get_settings()


class RankingService:
    """排行榜服务 - 处理投票统计和排行榜计算"""
    
    def __init__(self):
        self.db = None
    
    def get_db(self):
        """获取数据库实例"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    async def calculate_debate_result(self, debate_id: ObjectId) -> Optional[VoteResult]:
        """
        计算辩论结果
        
        Args:
            debate_id: 辩论ID
        
        Returns:
            投票结果对象
        """
        db = self.get_db()
        
        # 获取辩论信息
        debate = await db.debates.find_one({"_id": debate_id})
        if not debate:
            return None
        
        # 获取所有有效投票
        votes = await db.votes.find(
            {"debate_id": debate_id, "is_valid": True}
        ).to_list(length=None)
        
        if not votes:
            return None
        
        # 获取参与者模型信息
        participants = debate.get("participants", [])
        model_ids = [p["model_id"] for p in participants]
        model_display_names = {p["model_id"]: p["display_name"] for p in participants}
        
        # 统计各维度分数
        logic_scores = {mid: [] for mid in model_ids}
        persuasion_scores = {mid: [] for mid in model_ids}
        humor_scores = {mid: [] for mid in model_ids}
        preference_counts = {mid: 0 for mid in model_ids}
        
        for vote in votes:
            # 逻辑分数
            logic_score = vote.get("logic_score", {})
            for mid, score in logic_score.items():
                if mid in logic_scores:
                    logic_scores[mid].append(score)
            
            # 说服力分数
            persuasion_score = vote.get("persuasion_score", {})
            for mid, score in persuasion_score.items():
                if mid in persuasion_scores:
                    persuasion_scores[mid].append(score)
            
            # 幽默感分数
            humor_score = vote.get("humor_score", {})
            for mid, score in humor_score.items():
                if mid in humor_scores:
                    humor_scores[mid].append(score)
            
            # 偏好统计
            preferred = vote.get("preferred_model_id")
            if preferred and preferred in preference_counts:
                preference_counts[preferred] += 1
        
        # 计算平均分
        def calculate_average(scores: List) -> float:
            if not scores:
                return 0.0
            return round(sum(scores) / len(scores), 2)
        
        logic_averages = {mid: calculate_average(scores) for mid, scores in logic_scores.items()}
        persuasion_averages = {mid: calculate_average(scores) for mid, scores in persuasion_scores.items()}
        humor_averages = {mid: calculate_average(scores) for mid, scores in humor_scores.items()}
        
        # 计算综合评分（加权：逻辑40% + 说服力40% + 幽默感20%）
        overall_scores = {}
        for mid in model_ids:
            logic = logic_averages.get(mid, 0)
            persuasion = persuasion_averages.get(mid, 0)
            humor = humor_averages.get(mid, 0)
            
            overall = round(logic * 0.4 + persuasion * 0.4 + humor * 0.2, 2)
            overall_scores[mid] = overall
        
        # 确定获胜者（综合评分最高者）
        winner_model_id = None
        winner_display_name = None
        
        if overall_scores:
            winner_model_id = max(overall_scores, key=overall_scores.get)
            winner_display_name = model_display_names.get(winner_model_id)
        
        return VoteResult(
            debate_id=debate_id,
            logic_averages=logic_averages,
            persuasion_averages=persuasion_averages,
            humor_averages=humor_averages,
            preference_counts=preference_counts,
            total_votes=len(votes),
            overall_scores=overall_scores,
            winner_model_id=winner_model_id,
            winner_display_name=winner_display_name
        )
    
    async def update_model_stats_after_debate(
        self,
        debate_id: ObjectId,
        vote_result: VoteResult
    ):
        """
        更新模型统计数据（辩论结束后调用）
        
        Args:
            debate_id: 辩论ID
            vote_result: 投票结果
        """
        db = self.get_db()
        
        # 获取辩论信息
        debate = await db.debates.find_one({"_id": debate_id})
        if not debate:
            return
        
        category = debate.get("category", "general")
        participants = debate.get("participants", [])
        
        winner_model_id = vote_result.winner_model_id
        
        for participant in participants:
            model_id = participant["model_id"]
            model_name = participant["model_name"]
            display_name = participant["display_name"]
            
            # 确定胜负
            is_winner = model_id == winner_model_id
            
            # 获取该模型的各维度分数
            logic_score = vote_result.logic_averages.get(model_id, 0)
            persuasion_score = vote_result.persuasion_averages.get(model_id, 0)
            humor_score = vote_result.humor_averages.get(model_id, 0)
            overall_score = vote_result.overall_scores.get(model_id, 0)
            
            # 查找或创建模型统计
            model_stats = await db.model_stats.find_one({"model_id": model_id})
            
            if not model_stats:
                # 创建新的统计记录
                model_stats = {
                    "model_id": model_id,
                    "model_name": model_name,
                    "display_name": display_name,
                    "total_debates": 0,
                    "total_wins": 0,
                    "total_losses": 0,
                    "win_rate": 0.0,
                    "avg_logic_score": 0.0,
                    "avg_persuasion_score": 0.0,
                    "avg_humor_score": 0.0,
                    "avg_overall_score": 0.0,
                    "category_stats": {},
                    "recent_performance": [],
                    "style_tags": [],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            
            # 更新统计数据
            total_debates = model_stats["total_debates"] + 1
            total_wins = model_stats["total_wins"] + (1 if is_winner else 0)
            total_losses = model_stats["total_losses"] + (0 if is_winner else 1)
            win_rate = round(total_wins / total_debates, 2) if total_debates > 0 else 0.0
            
            # 更新平均分（加权平均）
            old_total = model_stats["total_debates"]
            new_avg_logic = round(
                (model_stats["avg_logic_score"] * old_total + logic_score) / total_debates, 2
            ) if total_debates > 0 else logic_score
            
            new_avg_persuasion = round(
                (model_stats["avg_persuasion_score"] * old_total + persuasion_score) / total_debates, 2
            ) if total_debates > 0 else persuasion_score
            
            new_avg_humor = round(
                (model_stats["avg_humor_score"] * old_total + humor_score) / total_debates, 2
            ) if total_debates > 0 else humor_score
            
            new_avg_overall = round(
                (model_stats["avg_overall_score"] * old_total + overall_score) / total_debates, 2
            ) if total_debates > 0 else overall_score
            
            # 更新分类统计
            category_stats = model_stats.get("category_stats", {})
            if category not in category_stats:
                category_stats[category] = {"wins": 0, "losses": 0, "win_rate": 0.0}
            
            cat_wins = category_stats[category]["wins"] + (1 if is_winner else 0)
            cat_losses = category_stats[category]["losses"] + (0 if is_winner else 1)
            cat_total = cat_wins + cat_losses
            cat_win_rate = round(cat_wins / cat_total, 2) if cat_total > 0 else 0.0
            
            category_stats[category] = {
                "wins": cat_wins,
                "losses": cat_losses,
                "win_rate": cat_win_rate
            }
            
            # 更新最近表现（保留最近10场）
            recent_performance = model_stats.get("recent_performance", [])
            recent_performance.append({
                "debate_id": str(debate_id),
                "result": "win" if is_winner else "loss",
                "score": overall_score,
                "category": category,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            if len(recent_performance) > 10:
                recent_performance = recent_performance[-10:]
            
            # 分析风格标签
            style_tags = self._analyze_style_tags(
                logic_score, persuasion_score, humor_score, 
                model_stats.get("style_tags", [])
            )
            
            # 准备更新数据
            update_data = {
                "$set": {
                    "total_debates": total_debates,
                    "total_wins": total_wins,
                    "total_losses": total_losses,
                    "win_rate": win_rate,
                    "avg_logic_score": new_avg_logic,
                    "avg_persuasion_score": new_avg_persuasion,
                    "avg_humor_score": new_avg_humor,
                    "avg_overall_score": new_avg_overall,
                    "category_stats": category_stats,
                    "recent_performance": recent_performance,
                    "style_tags": style_tags,
                    "updated_at": datetime.utcnow()
                }
            }
            
            # 插入或更新
            await db.model_stats.update_one(
                {"model_id": model_id},
                update_data,
                upsert=True
            )
    
    def _analyze_style_tags(
        self,
        logic_score: float,
        persuasion_score: float,
        humor_score: float,
        existing_tags: List[str]
    ) -> List[str]:
        """
        根据分数分析风格标签
        
        Args:
            logic_score: 逻辑分数
            persuasion_score: 说服力分数
            humor_score: 幽默感分数
            existing_tags: 现有标签
        
        Returns:
            更新后的风格标签
        """
        new_tags = set(existing_tags)
        
        # 根据各维度分数添加标签
        if logic_score >= 8:
            new_tags.add("logical")
        elif logic_score <= 5:
            new_tags.discard("logical")
        
        if persuasion_score >= 8:
            new_tags.add("persuasive")
        elif persuasion_score <= 5:
            new_tags.discard("persuasive")
        
        if humor_score >= 7:
            new_tags.add("humorous")
        elif humor_score <= 4:
            new_tags.discard("humorous")
        
        # 综合分析
        if logic_score > persuasion_score and logic_score > humor_score:
            new_tags.add("rational")
            new_tags.discard("emotional")
        elif persuasion_score > logic_score and persuasion_score > humor_score:
            new_tags.add("emotional")
            new_tags.discard("rational")
        
        return list(new_tags)
    
    async def get_overall_ranking(self, limit: int = 20) -> OverallRanking:
        """
        获取总体排行榜
        
        Args:
            limit: 返回数量限制
        
        Returns:
            总体排行榜
        """
        db = self.get_db()
        
        # 按胜率和综合评分排序
        cursor = db.model_stats.find(
            {"total_debates": {"$gte": 1}}  # 至少参加1场辩论
        ).sort([
            ("win_rate", -1),
            ("avg_overall_score", -1),
            ("total_debates", -1)
        ]).limit(limit)
        
        model_stats_list = await cursor.to_list(length=limit)
        
        rankings = []
        for idx, stats in enumerate(model_stats_list):
            rankings.append(RankingItem(
                model_id=stats["model_id"],
                model_name=stats["model_name"],
                display_name=stats["display_name"],
                rank=idx + 1,
                win_rate=stats["win_rate"],
                total_debates=stats["total_debates"],
                avg_overall_score=stats["avg_overall_score"],
                style_tags=stats.get("style_tags", [])
            ))
        
        return OverallRanking(
            updated_at=datetime.utcnow(),
            rankings=rankings
        )
    
    async def get_category_ranking(self, category: str, limit: int = 20) -> Optional[CategoryRanking]:
        """
        获取分类排行榜
        
        Args:
            category: 分类名称
            limit: 返回数量限制
        
        Returns:
            分类排行榜
        """
        db = self.get_db()
        
        # 查找有该分类数据的模型
        cursor = db.model_stats.find(
            {f"category_stats.{category}": {"$exists": True}}
        ).limit(limit)
        
        model_stats_list = await cursor.to_list(length=limit)
        
        if not model_stats_list:
            return None
        
        # 按分类胜率排序
        def get_category_win_rate(stats):
            cat_stats = stats.get("category_stats", {}).get(category, {})
            return cat_stats.get("win_rate", 0)
        
        model_stats_list.sort(key=get_category_win_rate, reverse=True)
        
        rankings = []
        for idx, stats in enumerate(model_stats_list):
            cat_stats = stats.get("category_stats", {}).get(category, {})
            
            rankings.append(RankingItem(
                model_id=stats["model_id"],
                model_name=stats["model_name"],
                display_name=stats["display_name"],
                rank=idx + 1,
                win_rate=cat_stats.get("win_rate", 0),
                total_debates=cat_stats.get("wins", 0) + cat_stats.get("losses", 0),
                avg_overall_score=stats["avg_overall_score"],
                style_tags=stats.get("style_tags", []),
                category_performance={
                    "wins": cat_stats.get("wins", 0),
                    "losses": cat_stats.get("losses", 0)
                }
            ))
        
        return CategoryRanking(
            category=category,
            updated_at=datetime.utcnow(),
            rankings=rankings
        )
    
    async def get_model_stats(self, model_id: str) -> Optional[ModelStats]:
        """
        获取单个模型的统计数据
        
        Args:
            model_id: 模型ID
        
        Returns:
            模型统计数据
        """
        db = self.get_db()
        
        stats = await db.model_stats.find_one({"model_id": model_id})
        if not stats:
            return None
        
        return ModelStats(**stats)
    
    async def get_all_categories(self) -> List[str]:
        """
        获取所有存在的分类
        
        Returns:
            分类列表
        """
        db = self.get_db()
        
        # 从model_stats中提取所有分类
        categories = set()
        
        async for stats in db.model_stats.find({"category_stats": {"$exists": True}}):
            cat_stats = stats.get("category_stats", {})
            for cat in cat_stats.keys():
                categories.add(cat)
        
        # 也可以从topics和debates中获取更多分类
        async for topic in db.topics.find({"category": {"$exists": True}}):
            if topic.get("category"):
                categories.add(topic["category"])
        
        return sorted(list(categories))


# 创建全局排行榜服务实例
ranking_service = RankingService()


def get_ranking_service() -> RankingService:
    """获取排行榜服务实例"""
    return ranking_service
