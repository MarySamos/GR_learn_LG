"""流式事件构建器

用于两阶段工作流的 Server-Sent Events 格式化
"""
import json


class StreamEvent:
    """流式事件构建器"""

    @staticmethod
    def intent(route_type: str, confidence: float = 0.0) -> str:
        """意图识别事件（兼容 route_type 和 intent 参数）"""
        return f"data: {json.dumps({'type': 'intent', 'route_type': route_type}, ensure_ascii=False)}\n\n"

    @staticmethod
    def thinking(message: str = "", step: str = "") -> str:
        """思考状态事件"""
        return f"data: {json.dumps({'type': 'thinking', 'message': message, 'step': step}, ensure_ascii=False)}\n\n"

    @staticmethod
    def rewritten(original: str, rewritten: str, reason: str) -> str:
        """查询重写事件"""
        return f"data: {json.dumps({'type': 'rewritten', 'original': original, 'rewritten': rewritten, 'reason': reason}, ensure_ascii=False)}\n\n"

    @staticmethod
    def sql(sql: str, corrected: bool = False) -> str:
        """SQL 事件"""
        return f"data: {json.dumps({'type': 'sql', 'sql': sql, 'corrected': corrected}, ensure_ascii=False)}\n\n"

    @staticmethod
    def query_result(row_count: int, preview: list = None) -> str:
        """查询结果事件"""
        return f"data: {json.dumps({'type': 'query_result', 'row_count': row_count, 'preview': preview or []}, ensure_ascii=False)}\n\n"

    @staticmethod
    def text(content: str) -> str:
        """文本内容事件"""
        return f"data: {json.dumps({'type': 'text', 'content': content}, ensure_ascii=False)}\n\n"

    @staticmethod
    def answer(content: str) -> str:
        """最终回答事件"""
        return f"data: {json.dumps({'type': 'answer', 'content': content}, ensure_ascii=False)}\n\n"

    @staticmethod
    def error(message: str) -> str:
        """错误事件"""
        return f"data: {json.dumps({'type': 'error', 'message': message}, ensure_ascii=False)}\n\n"

    @staticmethod
    def done() -> str:
        """完成事件"""
        return f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    @staticmethod
    def sources(sources: list) -> str:
        """RAG知识来源事件"""
        return f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"

    @staticmethod
    def chart_data(chart_type: str, x_data: list, y_data: list, title: str = "", series_name: str = "") -> str:
        """图表数据事件（JSON格式，前端用 ECharts 渲染）

        Args:
            chart_type: 图表类型 (bar/line/pie/radar)
            x_data: X轴数据
            y_data: Y轴数据
            title: 图表标题
            series_name: 系列名称
        """
        payload = {
            "type": "chart_data",
            "chart_type": chart_type,
            "x_data": x_data,
            "y_data": y_data,
            "title": title,
            "series_name": series_name,
        }
        return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
