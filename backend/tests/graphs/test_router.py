"""测试对话路由器"""
import pytest
from app.graphs.router import ConversationRouter
from app.graphs.memory import ConversationMemory
from app.graphs.enums import RouteType


@pytest.mark.anyio
async def test_route_chat_greeting():
    """测试问候路由到闲聊"""
    router = ConversationRouter()
    memory = ConversationMemory(session_id="s1", user_id="u1")

    decision = await router.route("你好", memory)

    assert decision.route_type == RouteType.CHAT
    assert decision.confidence > 0.7


@pytest.mark.anyio
async def test_route_chat_thanks():
    """测试感谢路由到闲聊"""
    router = ConversationRouter()
    memory = ConversationMemory(session_id="s1", user_id="u1")

    decision = await router.route("谢谢你的帮助", memory)

    assert decision.route_type == RouteType.CHAT


@pytest.mark.anyio
async def test_route_query():
    """测试查询路由"""
    router = ConversationRouter()
    memory = ConversationMemory(session_id="s1", user_id="u1")

    decision = await router.route("查询30岁以下的客户", memory)

    assert decision.route_type == RouteType.QUERY
    assert "age" in decision.extracted_entities


@pytest.mark.anyio
async def test_route_followup_explain():
    """测试解释型追问"""
    router = ConversationRouter()
    memory = ConversationMemory(session_id="s1", user_id="u1")
    memory.last_query = "查询30岁以下的客户"
    memory.current_topic = "30岁以下客户"

    decision = await router.route("为什么转化率这么低？", memory)

    assert decision.route_type == RouteType.FOLLOWUP
    assert decision.followup_type is not None


@pytest.mark.anyio
async def test_route_correction():
    """测试修正路由"""
    router = ConversationRouter()
    memory = ConversationMemory(session_id="s1", user_id="u1")
    memory.last_query = "查询30岁以下的客户"

    decision = await router.route("不是30岁，是40岁以上的", memory)

    assert decision.route_type == RouteType.CORRECTION
