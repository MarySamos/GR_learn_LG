"""两阶段对话工作流

第一阶段路由，第二阶段分发处理
"""
from typing import AsyncGenerator, TYPE_CHECKING, Optional

from app.graphs.router import ConversationRouter
from app.graphs.memory import ConversationMemory
from app.graphs.memory_manager import MemoryManager
from app.graphs.chat_handler import ChatHandler
from app.graphs.followup import FollowupAnalyzer
from app.graphs.tone import ToneAdapter
from app.graphs.stream_event import StreamEvent
from app.graphs.route_types import RouteDecision

# Lazy import to avoid ModuleNotFoundError when langgraph is not installed
if TYPE_CHECKING:
    from app.graphs.workflow import agent_app
    from app.graphs.state import create_initial_state


class TwoStageWorkflow:
    """两阶段对话工作流

    流程：
    1. 路由决策
    2. 分发处理（闲聊/查询/追问）
    3. 语气适配
    4. 返回结果
    """

    def __init__(self):
        self.router = ConversationRouter()
        self.chat_handler = ChatHandler()
        self.followup_analyzer = FollowupAnalyzer()
        self.tone_adapter = ToneAdapter()
        self.memory_manager = MemoryManager()

    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str = "default"
    ) -> AsyncGenerator[str, None]:
        """处理用户消息

        Args:
            message: 用户消息
            session_id: 会话 ID
            user_id: 用户 ID

        Yields:
            SSE 格式的事件字符串
        """
        try:
            # 1. 加载记忆
            memory = await self.memory_manager.get_or_create(session_id, user_id)

            # 2. 路由决策
            decision = await self.router.route(message, memory)
            yield StreamEvent.intent(decision.route_type.value)

            # 3. 分发处理
            if decision.route_type.value == "chat":
                async for chunk in self._handle_chat(message, memory):
                    yield chunk

            elif decision.route_type.value == "followup":
                async for chunk in self._handle_followup(message, memory):
                    yield chunk

            else:  # query or correction
                async for chunk in self._handle_query(message, memory, decision):
                    yield chunk

            # 4. 更新记忆
            await self.memory_manager.update(memory)

            yield StreamEvent.done()

        except Exception as e:
            yield StreamEvent.error(f"处理出错: {str(e)}")
            yield StreamEvent.done()

    async def _handle_chat(
        self,
        message: str,
        memory: ConversationMemory
    ) -> AsyncGenerator[str, None]:
        """处理闲聊"""
        yield StreamEvent.thinking("正在回复...")

        response = await self.chat_handler.chat(message, memory)
        adapted = self.tone_adapter.adapt(response, memory.last_intent or "chat")

        yield StreamEvent.answer(adapted)

    async def _handle_followup(
        self,
        message: str,
        memory: ConversationMemory
    ) -> AsyncGenerator[str, None]:
        """处理追问"""
        yield StreamEvent.thinking("正在分析...")

        action = await self.followup_analyzer.analyze(message, memory)

        if action.type == "NEW_QUERY":
            # 当新查询处理
            async for chunk in self._handle_query(message, memory, None):
                yield chunk
        else:
            response = await self.followup_analyzer.handle(action, memory)
            adapted = self.tone_adapter.adapt(response, memory.last_intent or "followup")

            yield StreamEvent.answer(adapted)

    async def _handle_query(
        self,
        message: str,
        memory: ConversationMemory,
        decision: Optional[RouteDecision] = None
    ) -> AsyncGenerator[str, None]:
        """处理数据查询"""
        yield StreamEvent.thinking("正在查询...")

        # Lazy import to avoid ModuleNotFoundError when langgraph is not installed
        from app.graphs.state import create_initial_state
        from app.graphs.workflow import agent_app

        # 构建初始状态
        initial_state = create_initial_state(
            user_input=message,
            chat_history=memory.messages
        )

        config = {
            "configurable": {
                "thread_id": memory.session_id,
                "user_id": memory.user_id,
            }
        }

        # 执行现有工作流
        final_state = await agent_app.ainvoke(initial_state, config=config)

        # 更新记忆
        if final_state.get("sql_result"):
            memory.update_after_query(
                query=message,
                sql=final_state.get("generated_sql", ""),
                result=final_state["sql_result"],
                intent=final_state.get("intent", "query")
            )

        # 发送 SQL 事件
        generated_sql = final_state.get("generated_sql")
        if generated_sql:
            yield StreamEvent.sql(generated_sql, final_state.get("sql_corrected", False))

        # 发送图表数据事件（JSON 格式，前端用 ECharts 渲染）
        sql_result = final_state.get("sql_result", [])
        if sql_result and len(sql_result) > 1:
            chart_info = self._extract_chart_data(sql_result, message)
            if chart_info:
                yield StreamEvent.chart_data(**chart_info)

        # RAG 知识来源事件
        rag_sources = final_state.get("rag_sources")
        if rag_sources:
            yield StreamEvent.sources(rag_sources)

        # 适配语气
        answer = final_state.get("final_answer", "抱歉，没有生成回答。")
        adapted = self.tone_adapter.adapt(
            answer,
            final_state.get("intent", "query"),
            has_data=bool(final_state.get("sql_result"))
        )

        yield StreamEvent.answer(adapted)

    @staticmethod
    def _extract_chart_data(sql_result: list, user_input: str = "") -> Optional[dict]:
        """从查询结果中自动提取图表数据

        Args:
            sql_result: SQL 查询结果列表
            user_input: 用户原始输入（用于推测图表类型）

        Returns:
            图表数据字典（chart_type, x_data, y_data, title, series_name）或 None
        """
        if not sql_result or len(sql_result) < 2:
            return None

        columns = list(sql_result[0].keys())
        if len(columns) < 2:
            return None

        # 识别分类列和数值列
        str_cols = []
        num_cols = []
        for col in columns:
            sample_val = sql_result[0].get(col)
            if isinstance(sample_val, (int, float)):
                num_cols.append(col)
            else:
                str_cols.append(col)

        if not str_cols or not num_cols:
            return None

        x_col = str_cols[0]
        y_col = num_cols[0]

        x_data = [str(row.get(x_col, "")) for row in sql_result]
        y_data = [row.get(y_col, 0) for row in sql_result]

        # 根据用户输入推测图表类型
        chart_type = "bar"
        input_lower = user_input.lower()
        if any(kw in input_lower for kw in ["饼图", "占比", "比例", "百分比", "pie"]):
            chart_type = "pie"
        elif any(kw in input_lower for kw in ["折线", "趋势", "变化", "line"]):
            chart_type = "line"
        elif any(kw in input_lower for kw in ["雷达", "radar"]):
            chart_type = "radar"

        # 生成标题
        title = f"{x_col} vs {y_col}"

        return {
            "chart_type": chart_type,
            "x_data": x_data,
            "y_data": y_data,
            "title": title,
            "series_name": y_col,
        }


# 全局实例
two_stage_workflow = TwoStageWorkflow()

