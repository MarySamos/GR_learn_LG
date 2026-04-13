"""
LangGraph 节点定义

优化内容：
1. Few-Shot Prompt 优化
2. SQL 错误自愈机制
3. 对话上下文增强
"""
import json
import logging
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from app.core.config import settings
from app.graphs.state import AgentState
from app.graphs.enums import Intent
from app.graphs.prompts import (
    get_intent_classification_prompt_with_examples,
    TEXT_TO_SQL_PROMPT,
    TEXT_TO_SQL_EXAMPLES,
    SQL_CORRECTION_PROMPT,
    GENERATE_ANSWER_WITH_CONTEXT_PROMPT,
    build_context_string,
    resolve_coreference,
    MARKETING_DATA_SCHEMA,
)
from app.graphs.tools import (
    execute_sql, get_basic_stats, get_column_distribution,
    get_conversion_rate, generate_chart, get_table_schema
)

logger = logging.getLogger(__name__)


# ========== LLM 管理器（支持不同 temperature）==========
class LLMManager:
    """LLM 管理器（按 temperature 缓存不同实例）"""

    _instances = {}

    @classmethod
    def get_llm(cls, temperature: float = 0.1) -> ChatOpenAI:
        """
        获取 LLM 实例

        Args:
            temperature: 温度参数

        Returns:
            ChatOpenAI 实例
        """
        if temperature not in cls._instances:
            cls._instances[temperature] = ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=temperature,
                openai_api_key=settings.ZHIPU_API_KEY,
                openai_api_base=settings.LLM_API_BASE
            )
        return cls._instances[temperature]


# 全局 LLM 实例
llm = LLMManager.get_llm(temperature=0.1)  # 低温度，提高准确性
creative_llm = LLMManager.get_llm(temperature=0.3)  # 稍高温度，用于生成回答


# ========== 错误处理装饰器 ==========
def handle_node_errors(node_name: str):
    """
    节点错误处理装饰器

    Args:
        node_name: 节点名称
    """
    def decorator(func):
        def wrapper(state: AgentState) -> dict:
            try:
                return func(state)
            except Exception as e:
                error_msg = f"{node_name}: {str(e)}"
                logger.error(f"节点执行失败: {error_msg}", exc_info=True)
                return {"error_message": error_msg}
        return wrapper
    return decorator


# ========== 辅助函数：SQL 修正（自愈机制）==========
def _correct_sql(sql: str, error: str, max_retries: int = 2) -> str:
    """
    SQL 修正函数 - 自愈机制核心

    Args:
        sql: 原始 SQL
        error: 错误信息
        max_retries: 最大重试次数

    Returns:
        修正后的 SQL 或原始 SQL（如果修正失败）
    """
    for attempt in range(max_retries):
        logger.info(f"🔧 SQL 修正尝试 {attempt + 1}/{max_retries}")

        correction_prompt = ChatPromptTemplate.from_messages([
            ("system", SQL_CORRECTION_PROMPT),
            ("user", "{sql}\n错误: {error}")
        ])

        chain = correction_prompt | llm | StrOutputParser()
        corrected_sql = chain.invoke({
            "sql": sql,
            "error": error,
            "schema": MARKETING_DATA_SCHEMA
        }).strip()

        # 清理 markdown 标记
        if corrected_sql.startswith("```"):
            corrected_sql = corrected_sql.split("```")[1]
        if corrected_sql.startswith("sql"):
            corrected_sql = corrected_sql[3:].strip()

        # 验证修正后的 SQL
        test_result = execute_sql(corrected_sql, max_rows=1)

        if test_result.get("success"):
            logger.info(f"✅ SQL 修正成功！")
            return corrected_sql
        else:
            logger.warning(f"⚠️ 修正后的 SQL 仍然错误: {test_result.get('error')}")
            # 更新错误信息用于下次修正
            error = test_result.get("error", "")
            sql = corrected_sql

    logger.error(f"❌ SQL 修正失败，已尝试 {max_retries} 次")
    return sql  # 返回最后一次尝试的结果


# ========== 节点 1: 意图识别（增强版 - Few-Shot）==========
@handle_node_errors("intent_parser")
def intent_parser(state: AgentState) -> dict:
    """
    意图识别节点（增强版 - 使用 Few-Shot 示例）

    分析用户输入，判断用户意图类型
    """
    user_input = state.get("user_input", "")
    chat_history = state.get("chat_history", [])

    logger.info(f"🔍 解析意图: {user_input[:50]}...")

    # 构建上下文（用于更准确的意图识别）
    context = ""
    if chat_history:
        context = f"\n对话上下文：\n{build_context_string(chat_history, max_turns=2)}"

    # 使用带 Few-Shot 示例的 Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_intent_classification_prompt_with_examples()),
        ("user", "用户输入：{input}{context}")
    ])

    chain = prompt | llm | JsonOutputParser()
    result = chain.invoke({
        "input": user_input,
        "context": context
    })

    intent = result.get("intent", Intent.CHAT)
    confidence = result.get("confidence", 0.5)

    logger.info(f"✅ 解析到意图: {intent} (置信度: {confidence})")

    return {"intent": intent}


# ========== 节点 2: 指代消解（新增）==========
def resolve_user_input(state: AgentState) -> dict:
    """
    指代消解节点

    将用户输入中的指代词（"它"、"那些"等）替换为实际内容
    """
    user_input = state.get("user_input", "")
    chat_history = state.get("chat_history", [])

    if not chat_history:
        return {"resolved_input": user_input}

    resolved = resolve_coreference(user_input, chat_history)

    if resolved != user_input:
        logger.info(f"🔄 指代消解: '{user_input}' -> '{resolved}'")
    else:
        logger.info(f"✓ 无需消解: {user_input}")

    return {"resolved_input": resolved}


# ========== 节点 3: Text-to-SQL==========
@handle_node_errors("text_to_sql")
def text_to_sql(state: AgentState) -> dict:
    """
    Text-to-SQL 节点

    将自然语言转换为 SQL 查询
    - 使用 Few-Shot 示例
    - 结合对话上下文
    """
    # 使用消解后的输入（如果有），否则使用原始输入
    user_input = state.get("resolved_input", state.get("user_input", ""))
    chat_history = state.get("chat_history", [])

    logger.info("📝 正在生成 SQL...")

    # 构建上下文信息
    context_info = ""
    if chat_history:
        last_turn = chat_history[-1] if isinstance(chat_history[-1], dict) else {"user": str(chat_history[-1])}
        last_question = last_turn.get("user", last_turn.get("question", ""))

        # 如果上轮是查询，这轮可能是在追问
        if last_question:
            context_info = f"\n上一轮用户问题：{last_question}\n"

    # 使用带 Few-Shot 示例的增强 Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", TEXT_TO_SQL_PROMPT),
        ("user", "{schema}{examples}{context}{user_input}")
    ])

    chain = prompt | llm | StrOutputParser()
    sql = chain.invoke({
        "schema": MARKETING_DATA_SCHEMA,
        "examples": TEXT_TO_SQL_EXAMPLES,
        "context": context_info,
        "user_input": user_input
    }).strip()

    # 清理 SQL（移除 markdown 代码块标记）
    if sql.startswith("```"):
        sql = sql.split("```")[1]
    if sql.startswith("sql"):
        sql = sql[3:].strip()
    if sql.endswith("```"):
        sql = sql[:-3].strip()

    logger.info(f"✅ 已生成 SQL: {sql[:100]}...")

    return {"generated_sql": sql}


# ========== 节点 4: 执行查询==========
@handle_node_errors("execute_query")
def execute_query(state: AgentState) -> dict:
    """
    执行 SQL 查询节点（

    执行 SQL 并返回结果，如果失败则自动修正后重试
    """
    logger.info("🔎 正在执行 SQL 查询...")

    sql = state.get("generated_sql", "")
    if not sql:
        raise ValueError("没有可执行的 SQL")

    # 首次执行
    result = execute_sql(sql)

    # 如果失败，尝试修正
    if not result.get("success"):
        error_msg = result.get("error", "")
        logger.warning(f"⚠️ SQL 执行失败: {error_msg}")

        # 触发自愈机制
        corrected_sql = _correct_sql(sql, error_msg)

        # 如果修正后的 SQL 与原 SQL 不同，再次执行
        if corrected_sql != sql:
            logger.info("🔄 使用修正后的 SQL 重新执行...")
            result = execute_sql(corrected_sql)

            if result.get("success"):
                logger.info("✅ 修正后的 SQL 执行成功！")
                return {
                    "sql_result": result["data"],
                    "generated_sql": corrected_sql,  # 更新为修正后的 SQL
                    "sql_corrected": True
                }

        # 如果仍然失败，返回错误信息
        return {"sql_error": result.get("error")}

    logger.info(f"✅ 查询执行成功，返回 {result['row_count']} 行")

    return {"sql_result": result["data"]}


# ========== 节点 5: 统计分析==========
@handle_node_errors("data_analysis")
def data_analysis(state: AgentState) -> dict:
    """
    统计分析节点（增强版）

    使用 LLM 智能选择分析工具并执行
    """
    logger.info("📊 正在执行数据分析...")

    user_input = state.get("user_input", "")
    chat_history = state.get("chat_history", [])

    # 定义可用的工具（增强版描述）
    tools_description = """## 可用分析工具

1. **get_basic_stats** - 获取基础统计信息
   - 总行数、列信息
   - 数值列的均值、中位数、标准差、最值
   - 分类列的分布情况

2. **get_column_distribution** - 获取单列的值分布
   - 需要参数: column_name（列名）
   - 返回该列各值的出现次数

3. **get_conversion_rate** - 计算转化率
   - 可选参数: group_by（分组列名）
   - 不分组则返回整体转化率
   - 分组则返回各组的转化率

## 工具选择建议

- 用户问"统计"、"总数"、"平均" → get_basic_stats
- 用户问"分布"、"占比"且指定某列 → get_column_distribution
- 用户问"转化率"、"成功率" → get_conversion_rate
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个数据分析助手。{tools_desc}

数据库结构：
{schema}

请根据用户输入，选择最合适的工具并提供参数。

返回 JSON 格式，例如：
{{'tool': 'get_basic_stats', 'params': {{}}}}
或
{{'tool': 'get_column_distribution', 'params': {{'column_name': 'job'}}}}
或
{{'tool': 'get_conversion_rate', 'params': {{'group_by': 'education'}}}}

参数说明：
- get_column_distribution 需要 column_name 参数
- get_conversion_rate 可选 group_by 参数"""),
        ("user", "{input}")
    ])

    chain = prompt | llm | JsonOutputParser()
    tool_config = chain.invoke({
        "input": user_input,
        "tools_desc": tools_description,
        "schema": MARKETING_DATA_SCHEMA
    })

    logger.info(f"🔧 已选择工具: {tool_config.get('tool')}")

    # 执行选定的工具
    tool_name = tool_config.get("tool")
    params = tool_config.get("params", {})

    if tool_name == "get_basic_stats":
        result = get_basic_stats()

    elif tool_name == "get_column_distribution":
        column = params.get("column_name", "job")
        result = get_column_distribution(column)

    elif tool_name == "get_conversion_rate":
        group_by = params.get("group_by")
        result = get_conversion_rate(group_by)

    else:
        raise ValueError(f"未知工具: {tool_name}")

    logger.info("✅ 数据分析完成")

    return {"stats_result": result}


# ========== 节点 6: 可视化==========
@handle_node_errors("visualization")
def visualization(state: AgentState) -> dict:
    """
    可视化节点（增强版）

    根据查询结果生成图表
    """
    logger.info("📊 正在生成可视化...")

    # 获取数据
    sql_result = state.get("sql_result", [])
    user_input = state.get("user_input", "")

    if not sql_result:
        raise ValueError("没有可用于可视化的数据")

    # 使用 LLM 决定图表类型和配置
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个可视化专家。请根据用户需求和数据特征，选择合适的图表类型。

## 可用图表类型

- **bar**: 柱状图（适合分类数据对比、排名）
- **line**: 折线图（适合趋势展示、时间序列）
- **pie**: 饼图（适合占比、百分比展示）
- **scatter**: 散点图（适合相关性分析）

## 选择建议

- 少于10个分类 → 柱状图
- 时间/月份相关 → 折线图
- 展示占比/百分比 → 饼图
- 数值相关性 → 散点图

返回 JSON 格式：
{{"chart_type": "图表类型", "x_column": "X轴列名", "y_column": "Y轴列名", "title": "图表标题"}}

注意：
- 如果数据中有 count、total、converted 等字段，优先选择这些作为 Y 轴
- 如果数据中有 job、education、marital 等分类字段，作为 X 轴
- 标题要简洁明了，概括数据内容"""),
        ("user", "用户需求：{input}\n数据预览：{data_preview}\n数据列：{columns}")
    ])

    # 准备数据预览（前3行）
    data_preview = json.dumps(sql_result[:3], ensure_ascii=False, default=str)
    columns = list(sql_result[0].keys()) if sql_result else []

    chain = prompt | llm | JsonOutputParser()
    chart_config = chain.invoke({
        "input": user_input,
        "data_preview": data_preview,
        "columns": columns
    })

    logger.info(f"📈 图表类型: {chart_config.get('chart_type')}")

    # 生成图表
    chart_html = generate_chart(
        data=sql_result,
        chart_type=chart_config.get("chart_type", "bar"),
        x_field=chart_config.get("x_column", columns[0] if columns else ""),
        y_field=chart_config.get("y_column", columns[1] if len(columns) > 1 else ""),
        title=chart_config.get("title", "数据可视化")
    )

    logger.info("✅ 图表生成成功")

    return {
        "chart_html": chart_html,
        "chart_type": chart_config.get("chart_type")
    }


# ========== 节点 7: RAG 知识检索==========
@handle_node_errors("knowledge_search")
def knowledge_search(state: AgentState) -> dict:
    """
    RAG 知识检索节点

    从 pgvector 中检索相似文档，结合上下文生成回答
    """
    logger.info("📚 正在检索知识库...")

    from app.services.rag_service import rag_service

    user_input = state.get("user_input", "")
    chat_history = state.get("chat_history", [])

    # 调用 RAG 服务（传入历史）
    rag_result = rag_service.rag_answer(
        query=user_input,
        top_k=5,
        chat_history=chat_history
    )

    sources_count = len(rag_result.get('sources', []))
    logger.info(f"✅ RAG 检索完成，找到 {sources_count} 个相关文档")

    return {
        "rag_context": rag_result["answer"],
        "rag_sources": rag_result["sources"],
        "final_answer": rag_result["answer"]
    }


# ========== 节点 8: 生成回答==========
@handle_node_errors("generate_answer")
def generate_answer(state: AgentState) -> dict:
    """
    生成最终回答节点（增强版）

    根据所有中间结果和对话历史生成用户友好的回答
    """
    logger.info("💬 正在生成最终回答...")

    user_input = state.get("user_input", "")
    chat_history = state.get("chat_history", [])
    intent = state.get("intent", Intent.CHAT)

    # RAG 意图已经在 knowledge_search 中生成了 final_answer，跳过
    if intent == Intent.RAG and state.get("final_answer"):
        logger.info("✅ 回答生成成功 (RAG 路径)")
        return {"final_answer": state["final_answer"]}

    # 构建执行结果摘要
    result_parts = []

    if intent == Intent.QUERY:
        sql = state.get("generated_sql", "")
        data = state.get("sql_result", [])
        was_corrected = state.get("sql_corrected", False)

        result_parts.append(f"执行的查询类型：{sql.split()[0].upper() if sql else 'SELECT'}")
        if was_corrected:
            result_parts.append("(SQL 已自动修正)")

        if data:
            result_parts.append(f"查询到 **{len(data)}** 条结果")

            # 智能选择要展示的示例数据
            sample_size = min(3, len(data))
            sample_data = data[:sample_size]

            # 格式化示例
            sample_str = "| " + " | ".join(list(sample_data[0].keys())[:5]) + " |\n"
            sample_str += "|" + "|".join(["---" for _ in range(min(5, len(sample_data[0].keys())))]) + "|\n"

            for row in sample_data:
                values = [str(v)[:20] for v in list(row.values())[:5]]
                sample_str += "| " + " | ".join(values) + " |\n"

            result_parts.append(f"\n数据示例（前{sample_size}条）：\n\n{sample_str}")

            if len(data) > sample_size:
                result_parts.append(f"\n*（还有 {len(data) - sample_size} 条结果未展示）*")

    elif intent == Intent.STATS:
        stats = state.get("stats_result") or {}
        if stats and "error" in stats:
            result_parts.append(f"分析出错：{stats['error']}")
        elif stats and "row_count" in stats:
            result_parts.append(f"分析了 **{stats['row_count']}** 行数据")
            if "numeric_stats" in stats:
                cols = list(stats["numeric_stats"].keys())[:3]
                result_parts.append(f"数值字段包括：{', '.join(cols)}")
            if "categorical_stats" in stats:
                cols = list(stats["categorical_stats"].keys())[:3]
                result_parts.append(f"分类字段包括：{', '.join(cols)}")

    elif intent == Intent.VIZ:
        data = state.get("sql_result", [])
        chart_type = state.get("chart_type", "")
        result_parts.append(f"已生成 **{chart_type}** 图表")
        result_parts.append(f"数据量：{len(data)} 条")

    # 如果有错误，包含错误信息
    if state.get("sql_error"):
        result_parts.append(f"\n⚠️ 查询出现问题：{state['sql_error']}")
        result_parts.append("\n建议：请检查查询条件是否合理，或换一种表述方式。")

    result_str = "\n".join(result_parts)

    # 构建对话上下文
    context_str = build_context_string(chat_history, max_turns=3)

    # 使用增强版 Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", GENERATE_ANSWER_WITH_CONTEXT_PROMPT),
        ("user", "{user_input}\n\n{chat_history}\n\n{execution_result}")
    ])

    chain = prompt | creative_llm | StrOutputParser()
    answer = chain.invoke({
        "user_input": user_input,
        "chat_history": context_str if context_str != "（无对话历史）" else "（无对话历史）",
        "execution_result": result_str
    })

    logger.info("✅ 回答生成成功")

    return {"final_answer": answer}
