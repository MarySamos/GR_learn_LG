"""闲聊 LLM Agent"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


class ChatAgent:
    """闲聊 LLM Agent

    使用高温度 LLM 进行自然对话
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.8,  # 高温度，更自然
            openai_api_key=settings.ZHIPU_API_KEY,
            openai_api_base=settings.LLM_API_BASE
        )
        self.parser = StrOutputParser()
        self._build_chain()

    def _build_chain(self):
        """构建闲聊链"""
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是 Z-Rop，一个亲切友好的银行数据分析助手。

## 你的特点
- 专业但不刻板，可以适当使用 😊 等表情
- 热情帮助用户了解数据
- 如果用户问银行业务知识，尽力回答
- 记住用户之前说过的内容

## 你的能力
- 帮助查询和分析银行营销数据
- 解读数据趋势和洞察
- 回答银行业务相关问题
- 进行友好的对话交流

回答风格：
- 简洁自然，不要太啰嗦
- 适当使用 emoji 增加亲和力
- 如果不知道，诚实地说不知道"""),
            ("user", """## 对话历史
{history}

## 用户说
{message}

请回复：""")
        ])

        self.chain = self.prompt | self.llm | self.parser

    async def chat(self, message: str, history: str) -> str:
        """进行闲聊

        Args:
            message: 用户消息
            history: 对话历史

        Returns:
            回复内容
        """
        return await self.chain.ainvoke({
            "message": message,
            "history": history or "（这是我们对话的开始）"
        })
