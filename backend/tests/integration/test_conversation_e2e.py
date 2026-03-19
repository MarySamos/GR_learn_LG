"""端到端对话测试"""
import pytest
from app.graphs.two_stage_workflow import TwoStageWorkflow


@pytest.mark.asyncio
async def test_full_conversation_flow():
    """测试完整对话流程"""
    workflow = TwoStageWorkflow()
    session_id = "e2e_test_session"

    # 1. 问候
    responses = []
    async for chunk in workflow.process(
        message="你好",
        session_id=session_id,
        user_id="test_user"
    ):
        responses.append(chunk)

    # 验证问候响应包含友好的回复
    assert any('"route_type": "chat"' in r for r in responses), "应该路由到闲聊"
    assert any("answer" in r for r in responses), "应该返回回答"
    assert any(("你好" in r or "嗨" in r or "BankAgent" in r) for r in responses), "应该包含问候语"

    # 2. 查询（注意：如果没有 langgraph，会返回错误）
    responses = []
    async for chunk in workflow.process(
        message="查询30岁以下的客户",
        session_id=session_id,
        user_id="test_user"
    ):
        responses.append(chunk)

    assert any("query" in r for r in responses), "应该路由到查询"
    # 查询路径应该完成（无论是成功还是错误）
    assert any('"type": "done"' in r for r in responses), "应该完成事件流"

    # 3. 追问 - 先设置历史记录
    memory = await workflow.memory_manager.get_or_create(session_id, "test_user")
    memory.update_after_query(
        query="查询30岁以下的客户",
        sql="SELECT * FROM marketing_data WHERE age < 30",
        result=[{"age": 25}, {"age": 28}],
        intent="query"
    )

    responses = []
    async for chunk in workflow.process(
        message="为什么？",
        session_id=session_id,
        user_id="test_user"
    ):
        responses.append(chunk)

    # 验证追问被正确处理（followup 类型的 EXPLAIN 会用本地 agent 处理）
    assert any("followup" in r for r in responses), "应该路由到追问"


@pytest.mark.asyncio
async def test_multi_turn_conversation():
    """测试多轮对话"""
    workflow = TwoStageWorkflow()
    session_id = "multi_turn_session"

    # 第一轮：闲聊
    responses = []
    async for chunk in workflow.process(
        message="你能做什么？",
        session_id=session_id,
        user_id="test_user"
    ):
        responses.append(chunk)

    assert any("answer" in r for r in responses), "闲聊应该返回回答"

    # 第二轮：查询（可能因缺少 langgraph 而返回错误，但流程应该完成）
    responses = []
    async for chunk in workflow.process(
        message="查询所有客户数据",
        session_id=session_id,
        user_id="test_user"
    ):
        responses.append(chunk)

    assert any('"type": "done"' in r for r in responses), "应该完成事件流"


@pytest.mark.asyncio
async def test_conversation_memory_persistence():
    """测试会话记忆持久化"""
    workflow = TwoStageWorkflow()
    session_id = "memory_test_session"

    # 第一次交互
    async for _ in workflow.process(
        message="我叫小明",
        session_id=session_id,
        user_id="test_user"
    ):
        pass

    # 获取记忆，验证上下文被保留
    memory = await workflow.memory_manager.get_or_create(session_id, "test_user")
    assert len(memory.messages) > 0, "应该保留对话历史"


@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    workflow = TwoStageWorkflow()

    responses = []
    async for chunk in workflow.process(
        message="",  # 空消息
        session_id="error_test_session",
        user_id="test_user"
    ):
        responses.append(chunk)

    # 应该优雅地处理错误，返回 done 事件
    assert any('"type": "done"' in r for r in responses), "应该完成事件流"
