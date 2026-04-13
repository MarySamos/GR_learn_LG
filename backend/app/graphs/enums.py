"""枚举类型定义（增强版）.

定义应用中使用的各种枚举类型
"""
from enum import Enum


class Intent(str, Enum):
    """用户意图类型"""

    # ========== 数据查询类 ==========
    QUERY = "query"           # 简单数据查询
    QUERY_COUNT = "query_count"  # 数量统计查询
    QUERY_LIST = "query_list"    # 列表查询

    # ========== 统计分析类 ==========
    STATS = "stats"           # 统计分析
    STATS_AGG = "stats_agg"     # 聚合统计（平均值、中位数等）
    STATS_DIST = "stats_dist"   # 分布分析
    STATS_CORR = "stats_corr"   # 相关性分析

    # ========== 可视化类 ==========
    VIZ = "viz"               # 可视化
    VIZ_BAR = "viz_bar"         # 柱状图
    VIZ_LINE = "viz_line"       # 折线图
    VIZ_PIE = "viz_pie"         # 饼图
    VIZ_SCATTER = "viz_scatter" # 散点图

    # ========== 知识问答类 ==========
    RAG = "rag"               # 知识问答

    # ========== 普通聊天类 ==========
    CHAT = "chat"             # 普通聊天
    GREETING = "greeting"       # 问候
    THANKS = "thanks"           # 感谢
    FAREWELL = "farewell"       # 告别

    # ========== 追问类 ==========
    WHY = "why"               # 为什么追问
    HOW = "how"               # 如何追问
    EXPLAIN = "explain"         # 解释追问

    @classmethod
    def get_main_intent(cls, intent: str) -> str:
        """获取主要意图类别（用于路由）"""
        if intent.startswith("query"):
            return "query"
        if intent.startswith("stats"):
            return "stats"
        if intent.startswith("viz"):
            return "viz"
        if intent == "rag":
            return "rag"
        return "chat"


class QueryComplexity(str, Enum):
    """查询复杂度"""
    SIMPLE = "simple"         # 单条件查询
    MEDIUM = "medium"         # 多条件查询
    COMPLEX = "complex"       # 复杂聚合/子查询


class VisualizationType(str, Enum):
    """可视化类型"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    RADAR = "radar"
    BOX_PLOT = "box_plot"


class RouteType(str, Enum):
    """路由类型"""
    CHAT = "chat"            # 闲聊
    QUERY = "query"          # 数据查询
    FOLLOWUP = "followup"    # 追问
    CORRECTION = "correction"  # 修正


class FollowupType(str, Enum):
    """追问类型"""
    EXPLAIN = "explain"      # 解释原因
    DETAIL = "detail"        # 展开细节
    DRILLDOWN = "drilldown"  # 下钻细分
    COMPARE = "compare"      # 对比
    TREND = "trend"          # 趋势
