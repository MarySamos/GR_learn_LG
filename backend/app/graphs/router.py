"""对话路由器

根据用户输入判断路由到哪个处理器
"""
from typing import Optional
from app.graphs.route_types import RouteDecision
from app.graphs.enums import RouteType, FollowupType
from app.graphs.memory import ConversationMemory
from app.graphs.agents.router_agent import RouterAgent


class ConversationRouter:
    """对话路由器

    判断用户意图，分发到对应处理器
    """

    def __init__(self):
        self.agent = RouterAgent()

    async def route(
        self,
        message: str,
        memory: ConversationMemory
    ) -> RouteDecision:
        """路由决策

        Args:
            message: 用户消息
            memory: 对话记忆

        Returns:
            路由决策
        """
        # 构建上下文
        context = self._format_context(memory)
        query_history = memory.get_last_query_summary()

        # 调用 LLM Agent
        agent_result = await self.agent.route(message, context, query_history)

        # 解析结果（归一化为小写）
        route_type_str = agent_result.get("route_type", "chat").lower()
        try:
            route_type = RouteType(route_type_str)
        except ValueError:
            # 如果返回值不合法，默认 CHAT
            route_type = RouteType.CHAT

        confidence = agent_result.get("confidence", 0.5)
        reasoning = agent_result.get("reasoning", "")

        # 后处理：如果 LLM 归类为 QUERY 但消息包含追问词且有历史，修正为 FOLLOWUP
        if route_type == RouteType.QUERY and memory.has_query_history():
            followup_keywords = ["为什么", "怎么样", "分析", "详细", "展开", "转化率"]
            if any(keyword in message for keyword in followup_keywords):
                route_type = RouteType.FOLLOWUP
                reasoning = f"修正为FOLLOWUP: {reasoning}"

        # 提取实体（如果是查询类型）
        extracted_entities = {}
        if route_type in (RouteType.QUERY, RouteType.CORRECTION):
            extracted_entities = memory.extract_filters(message)

        # 判断追问类型
        followup_type = None
        drilldown_dimension = None
        if route_type == RouteType.FOLLOWUP:
            followup_type = self._detect_followup_type(message)
            if followup_type == FollowupType.DRILLDOWN:
                drilldown_dimension = self._extract_drilldown_dimension(message)

        return RouteDecision(
            route_type=route_type,
            confidence=confidence,
            reasoning=reasoning,
            extracted_entities=extracted_entities,
            followup_type=followup_type,
            drilldown_dimension=drilldown_dimension
        )

    def _format_context(self, memory: ConversationMemory) -> str:
        """格式化上下文"""
        if not memory.messages:
            return "（无对话历史）"

        # 只取最近3轮
        recent = memory.messages[-6:]  # 6条 = 3轮
        parts = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            parts.append(f"{role}: {msg['content']}")

        return "\n".join(parts)

    def _detect_followup_type(self, message: str) -> Optional[FollowupType]:
        """检测追问类型"""
        # 解释型
        if any(word in message for word in ["为什么", "什么意思", "解释"]):
            return FollowupType.EXPLAIN

        # 展开型
        if any(word in message for word in ["详细", "展开", "多说", "更多"]):
            return FollowupType.DETAIL

        # 下钻型
        if any(word in message for word in ["按", "细分", "分组", "分别"]):
            return FollowupType.DRILLDOWN

        # 对比型
        if any(word in message for word in ["对比", "比较", "相差"]):
            return FollowupType.COMPARE

        # 趋势型
        if any(word in message for word in ["趋势", "变化", "增长"]):
            return FollowupType.TREND

        return None

    def _extract_drilldown_dimension(self, message: str) -> Optional[str]:
        """提取下钻维度"""
        # 检测常见维度
        dimensions = {
            "职业": "job",
            "job": "job",
            "教育": "education",
            "education": "education",
            "婚姻": "marital",
            "marital": "marital",
            "年龄": "age",
        }

        for key, value in dimensions.items():
            if key in message:
                return value

        return None
