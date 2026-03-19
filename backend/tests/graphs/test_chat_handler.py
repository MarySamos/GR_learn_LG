"""测试闲聊处理器"""
import pytest
from app.graphs.chat_handler import ChatHandler
from app.graphs.memory import ConversationMemory


@pytest.mark.anyio
async def test_greeting():
    """测试问候响应"""
    handler = ChatHandler()
    memory = ConversationMemory(session_id="s1", user_id="u1")

    response = await handler.chat("你好", memory)

    assert response
    assert len(response) > 5
    # 应该比较友好
    assert any(word in response for word in ["你好", "嗨", "😊", "助手"])


@pytest.mark.anyio
async def test_with_context():
    """测试带上下文的闲聊"""
    handler = ChatHandler()
    memory = ConversationMemory(session_id="s1", user_id="u1")
    memory.messages = [
        {"role": "user", "content": "我叫小明"},
        {"role": "assistant", "content": "你好小明！"}
    ]

    response = await handler.chat("我刚才说我叫什么？", memory)

    assert "小明" in response
