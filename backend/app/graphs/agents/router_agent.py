"""路由 LLM Agent

使用 LLM 进行智能路由决策
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import settings


class RouterAgent:
    """路由 LLM Agent"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.1,  # 低温度，确保稳定
            openai_api_key=settings.ZHIPU_API_KEY,
            openai_api_base=settings.LLM_API_BASE
        )
        self.parser = JsonOutputParser()
        self._build_chain()

    def _build_chain(self):
        """构建路由链"""
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是对话路由器。根据用户输入判断路由类型。

## 路由类型

1. **CHAT** - 闲聊、问候、感谢、告别
   - 问候：你好、嗨、在吗
   - 感谢：谢谢、感谢、多谢
   - 告别：再见、拜拜
   - 能力询问：你能做什么、你会什么

2. **QUERY** - 数据查询请求
   - 包含"查询"、"显示"、"列出"、"有多少"、"统计"
   - 包含具体条件（年龄、职业等）
   - 明确的数据查询意图

3. **FOLLOWUP** - 追问之前的结果
   - 追问词：为什么、怎么样、分析一下、详细说、展开
   - 代词：它、它们、那些、这个、转化率
   - 要求：需要有查询历史或上下文提及

4. **CORRECTION** - 修正之前的查询
   - 修正词：不是、错了、重新、换、除了
   - 要求是针对上一次查询的修正

## 判断逻辑

1. 先判断是否是问候/感谢/告别 → CHAT
2. 判断是否是修正（"不是X，是Y"）→ CORRECTION
3. **重要**：判断是否是追问（有历史 + 追问词）→ FOLLOWUP
   - 例如："为什么转化率这么低"应归类为FOLLOWUP
4. 判断是否是数据查询 → QUERY
5. 默认 → CHAT

## 输出格式

返回 JSON：
```json
{{
  "route_type": "CHAT|QUERY|FOLLOWUP|CORRECTION",
  "confidence": 0.9,
  "reasoning": "判断理由"
}}
```

注意：
- confidence 是 0-1 的置信度
- reasoning 简要说明判断依据（中文）
- route_type 使用大写字母（CHAT, QUERY, FOLLOWUP, CORRECTION）"""),
            ("user", """## 用户输入
{message}

## 对话上下文
{context}

## 查询历史
{query_history}

请返回路由决策：""")
        ])

        self.chain = self.prompt | self.llm | self.parser

    async def route(
        self,
        message: str,
        context: str,
        query_history: str
    ) -> Dict[str, Any]:
        """执行路由

        Args:
            message: 用户消息
            context: 对话上下文
            query_history: 查询历史

        Returns:
            路由决策字典
        """
        try:
            result = await self.chain.ainvoke({
                "message": message,
                "context": context or "（无）",
                "query_history": query_history or "（无）"
            })
            return result
        except Exception as e:
            # 降级：基于规则的简单路由
            return self._fallback_route(message)

    def _fallback_route(self, message: str) -> Dict[str, Any]:
        """降级路由（基于规则）"""
        # 问候/感谢/告别
        if any(word in message for word in ["你好", "嗨", "在吗", "谢谢", "感谢", "再见", "拜拜"]):
            return {"route_type": "CHAT", "confidence": 0.8, "reasoning": "匹配问候词"}

        # 修正
        if any(word in message for word in ["不是", "错了", "重新", "换"]):
            return {"route_type": "CORRECTION", "confidence": 0.7, "reasoning": "匹配修正词"}

        # 追问（优先级高于查询）
        if any(word in message for word in ["为什么", "怎么样", "分析", "详细", "展开", "转化率", "这个", "那些"]):
            return {"route_type": "FOLLOWUP", "confidence": 0.6, "reasoning": "匹配追问词"}

        # 数据查询关键词
        if any(word in message for word in ["查询", "显示", "统计", "多少", "列表"]):
            return {"route_type": "QUERY", "confidence": 0.7, "reasoning": "匹配查询词"}

        # 默认闲聊
        return {"route_type": "CHAT", "confidence": 0.5, "reasoning": "默认分类"}
