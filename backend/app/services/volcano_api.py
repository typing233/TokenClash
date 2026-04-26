import httpx
from typing import AsyncGenerator, Optional, Dict, Any, List
from app.config import get_settings


settings = get_settings()


class VolcanoAPIClient:
    """火山方舟API客户端封装"""
    
    def __init__(self):
        self.base_url = settings.volcano_base_url
        self.api_key = settings.volcano_api_key
        self.timeout = 60.0  # 超时时间60秒
    
    async def chat_completion(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 0.9,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        非流式对话调用
        
        Args:
            model_name: 模型名称
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            top_p: top_p参数
            stream: 是否流式输出
        
        Returns:
            API响应结果
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def chat_completion_stream(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 0.9
    ) -> AsyncGenerator[str, None]:
        """
        流式对话调用
        
        Args:
            model_name: 模型名称
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            top_p: top_p参数
        
        Yields:
            流式输出的内容片段
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": True
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    
    async def generate_argument(
        self,
        model_name: str,
        topic: str,
        side: str,  # "affirmative" or "negative"
        stage: str,  # "opening", "cross_examination", "closing"
        round_number: int = 1,
        context_messages: Optional[List[Dict[str, str]]] = None,
        opponent_argument: Optional[str] = None
    ) -> str:
        """
        生成辩论论点
        
        Args:
            model_name: 模型名称
            topic: 辩论话题
            side: 立场（正方/反方）
            stage: 辩论阶段
            round_number: 当前轮次
            context_messages: 上下文消息
            opponent_argument: 对方论点（用于反驳）
        
        Returns:
            生成的辩论内容
        """
        system_prompt = self._build_system_prompt(side, stage, topic)
        
        user_prompt = self._build_user_prompt(
            topic=topic,
            side=side,
            stage=stage,
            round_number=round_number,
            opponent_argument=opponent_argument
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 添加上下文消息（如果有）
        if context_messages:
            messages = context_messages + messages[1:]  # 保留system prompt
        
        response = await self.chat_completion(
            model_name=model_name,
            messages=messages,
            temperature=0.8,
            max_tokens=settings.max_message_length
        )
        
        return response["choices"][0]["message"]["content"]
    
    def _build_system_prompt(self, side: str, stage: str, topic: str) -> str:
        """构建系统提示词"""
        side_name = "正方" if side == "affirmative" else "反方"
        
        base_prompt = f"""你是一个专业的辩手，现在正在参加一场关于「{topic}」的辩论。
你的立场是：{side_name}。
请根据当前辩论阶段，给出精彩、有逻辑、有说服力的论点。

要求：
1. 保持专业、理性的辩论风格
2. 论点要有逻辑支撑，可以使用数据、例子等增强说服力
3. 语言要流畅、自然，适合口头表达
4. 注意辩论的礼貌和规范
5. 字数控制在300-500字左右"""
        
        stage_specific = ""
        if stage == "opening":
            stage_specific = """
当前阶段：开篇陈词
这是辩论的开始，你需要：
1. 清晰阐述你的立场和核心观点
2. 提出2-3个主要论点
3. 为后续辩论埋下伏笔"""
        elif stage == "cross_examination":
            stage_specific = """
当前阶段：交叉反驳
这是辩论的核心交锋阶段，你需要：
1. 针对对方的论点进行有力的反驳
2. 维护和强化自己的论点
3. 可以使用反问、类比等技巧
4. 注意抓住对方的逻辑漏洞"""
        elif stage == "closing":
            stage_specific = """
当前阶段：总结陈词
这是辩论的最后阶段，你需要：
1. 总结整场辩论的核心交锋
2. 再次强调自己论点的优势
3. 给观众留下深刻的印象
4. 不要提出新的论点，只做总结"""
        
        return base_prompt + stage_specific
    
    def _build_user_prompt(
        self,
        topic: str,
        side: str,
        stage: str,
        round_number: int,
        opponent_argument: Optional[str] = None
    ) -> str:
        """构建用户提示词"""
        side_name = "正方" if side == "affirmative" else "反方"
        
        prompt = f"""辩论话题：「{topic}」
你的立场：{side_name}
当前阶段：{self._get_stage_name(stage)}
当前轮次：第{round_number}轮"""
        
        if opponent_argument and stage == "cross_examination":
            prompt += f"""

对方刚刚说：
「{opponent_argument}」

请针对对方的论点进行反驳，同时维护自己的立场。"""
        
        if stage == "opening":
            prompt += """

请开始你的开篇陈词，清晰阐述你的立场和核心观点。"""
        elif stage == "closing":
            prompt += """

请开始你的总结陈词，总结整场辩论，强调你的论点优势。"""
        
        return prompt
    
    def _get_stage_name(self, stage: str) -> str:
        """获取阶段的中文名称"""
        stage_map = {
            "opening": "开篇陈词",
            "cross_examination": "交叉反驳",
            "closing": "总结陈词"
        }
        return stage_map.get(stage, stage)


# 创建全局客户端实例
volcano_client = VolcanoAPIClient()


def get_volcano_client() -> VolcanoAPIClient:
    """获取火山方舟API客户端"""
    return volcano_client
