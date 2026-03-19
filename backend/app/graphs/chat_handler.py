"""闲聊处理器

处理非数据查询的对话
"""
from app.graphs.memory import ConversationMemory
from app.graphs.agents.chat_agent import ChatAgent


class ChatHandler:
    """闲聊处理器

    处理问候、闲聊、感谢等非数据查询对话
    """

    def __init__(self):
        self.agent = ChatAgent()

    async def chat(
        self,
        message: str,
        memory: ConversationMemory
    ) -> str:
        """处理闲聊

        Args:
            message: 用户消息
            memory: 对话记忆

        Returns:
            回复内容
        """
        # 格式化历史
        history = self._format_history(memory)

        # 调用 Agent
        response = await self.agent.chat(message, history)

        # 更新记忆
        memory.add_message("user", message)
        memory.add_message("assistant", response)

        return response

    def _format_history(self, memory: ConversationMemory) -> str:
        """格式化对话历史"""
        if not memory.messages:
            return "（这是我们对话的开始）"

        # 只取最近5轮
        recent = memory.messages[-10:]
        parts = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "我"
            parts.append(f"{role}: {msg['content']}")

        return "\n".join(parts)
