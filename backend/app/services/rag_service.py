"""
RAG 知识问答服务（增强版 - 支持智谱AI Embedding）

基于 pgvector 向量检索 + LLM 生成的 RAG 链路：
1. 用户问题 → 智谱AI Embedding-3 向量化
2. pgvector 余弦距离检索 Top-K 知识文档
3. 检索结果作为上下文 → LLM 生成回答

增强功能：
- 对话历史感知
- 查询重写优化
- 混合检索策略
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings

logger = logging.getLogger(__name__)

# 智谱AI Embedding API配置
_ZHIPU_EMBEDDING_API = "https://open.bigmodel.cn/api/paas/v4/embeddings"
_ZHIPU_EMBEDDING_MODEL = "embedding-2"  # embedding-2 (1024维) 或 embedding-3 (2048维)
_EMBEDDING_DIM = 1024


class ZhipuEmbeddings:
    """智谱AI Embedding 封装"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def embed_query(self, text: str) -> List[float]:
        """将文本向量化"""
        try:
            response = requests.post(
                _ZHIPU_EMBEDDING_API,
                headers=self.headers,
                json={
                    "model": _ZHIPU_EMBEDDING_MODEL,
                    "input": text
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # 智谱AI返回格式: {"data": [{"embedding": [...]}]}
            if "data" in result and len(result["data"]) > 0:
                return result["data"][0]["embedding"]
            else:
                logger.error(f"智谱AI Embedding 响应格式错误: {result}")
                return [0.0] * _EMBEDDING_DIM

        except Exception as e:
            logger.error(f"智谱AI Embedding 调用失败: {str(e)}")
            return [0.0] * _EMBEDDING_DIM

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量向量化"""
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_query(text))
        return embeddings


class RAGService:
    """RAG 知识问答服务"""

    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)

        # 使用智谱AI的Embedding
        api_key = settings.ZHIPU_API_KEY or settings.OPENAI_API_KEY
        self.embeddings = ZhipuEmbeddings(api_key)

        # LLM（使用智谱AI）
        self.llm = ChatOpenAI(
            openai_api_key=api_key,
            openai_api_base=settings.LLM_API_BASE or settings.OPENAI_API_BASE,
            model=settings.LLM_MODEL,
            temperature=0.1
        )

    def embed_query(self, query: str) -> List[float]:
        """
        将用户问题向量化

        Args:
            query: 用户问题文本

        Returns:
            1024维向量（智谱AI embedding-3）
        """
        return self.embeddings.embed_query(query)

    def search_similar(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        pgvector 余弦距离检索 Top-K 相似文档

        Args:
            query: 用户问题
            top_k: 返回最相似的前 K 个文档
            similarity_threshold: 相似度阈值

        Returns:
            相似文档列表
        """
        logger.info(f"🔍 RAG 检索: {query[:50]}...")

        try:
            # 1. 问题向量化
            query_vector = self.embed_query(query)
            vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

            # 2. pgvector 余弦距离检索
            sql = text("""
                SELECT
                    id, title, content, file_path,
                    1 - (embedding <=> :query_vec) AS similarity
                FROM knowledge_docs
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> :query_vec
                LIMIT :top_k
            """)

            session = self.Session()
            try:
                result = session.execute(sql, {
                    "query_vec": vector_str,
                    "top_k": top_k
                })

                docs = []
                for row in result:
                    similarity = float(row.similarity)
                    if similarity >= similarity_threshold:
                        docs.append({
                            "id": row.id,
                            "title": row.title,
                            "content": row.content,
                            "file_path": row.file_path,
                            "similarity": round(similarity, 4)
                        })

                logger.info(f"✅ 检索到 {len(docs)} 个相关文档")
                return docs

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ RAG 检索失败: {str(e)}")
            return []

    def _rewrite_query_with_context(
        self,
        query: str,
        chat_history: List[Dict[str, str]]
    ) -> str:
        """
        基于对话历史重写查询（上下文感知）

        Args:
            query: 原始查询
            chat_history: 对话历史

        Returns:
            重写后的查询
        """
        if not chat_history:
            return query

        # 构建历史上下文
        history_text = ""
        if chat_history:
            last_turn = chat_history[-1]
            if isinstance(last_turn, dict):
                last_q = last_turn.get("user", last_turn.get("question", ""))
                last_a = last_turn.get("assistant", last_turn.get("answer", ""))
                history_text = f"上一轮：\n问题：{last_q}\n回答：{last_a[:200]}"

        # 如果查询很短，可能需要结合上下文
        if len(query) < 15 and chat_history:
            rewrite_prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个查询重写助手。请将用户的简短追问转换为完整的独立问题。

规则：
1. 如果用户使用指代词（"它"、"那些"、"这个"），替换为实际指代的内容
2. 保持问题简洁，不要添加不必要的信息
3. 只返回重写后的问题，不要解释"""),
                ("user", "{history}\n\n当前追问：{query}\n\n重写后的完整问题：")
            ])

            try:
                chain = rewrite_prompt | self.llm | StrOutputParser()
                rewritten = chain.invoke({
                    "history": history_text,
                    "query": query
                }).strip()

                logger.info(f"🔄 查询重写: '{query}' -> '{rewritten}'")
                return rewritten
            except Exception as e:
                logger.warning(f"⚠️ 查询重写失败: {e}")

        return query

    def rag_answer(
        self,
        query: str,
        top_k: int = 5,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        完整的 RAG 链路：检索 + 生成（增强版 - 支持对话历史）

        Args:
            query: 用户问题
            top_k: 检索的文档数量
            chat_history: 聊天历史

        Returns:
            {
                "answer": "生成的回答",
                "sources": [{"title": ..., "content": ..., "similarity": ...}],
                "has_context": True/False
            }
        """
        # 1. 查询重写（如果需要）
        rewritten_query = self._rewrite_query_with_context(query, chat_history or [])

        # 2. 检索相似文档
        docs = self.search_similar(rewritten_query, top_k=top_k)

        # 3. 组装上下文
        if docs:
            context_parts = []
            for i, doc in enumerate(docs, 1):
                context_parts.append(
                    f"【文档{i}】{doc['title']}\n"
                    f"相似度: {doc['similarity']}\n"
                    f"内容: {doc['content']}\n"
                )
            context = "\n---\n".join(context_parts)
        else:
            context = "未找到相关知识文档。"

        # 4. 构建对话历史上下文
        history_context = ""
        if chat_history:
            history_lines = []
            for turn in chat_history[-2:]:  # 只取最近2轮
                if isinstance(turn, dict):
                    q = turn.get("user", turn.get("question", ""))
                    a = turn.get("assistant", turn.get("answer", ""))
                    history_lines.append(f"Q: {q}\nA: {a[:100]}...")
            if history_lines:
                history_context = f"\n## 对话历史\n{chr(10).join(history_lines)}\n"

        # 5. 构建 Prompt（增强版）
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是银行智能助手 Z-Rop，专门回答银行业务和金融知识相关问题。

请基于以下检索到的知识文档来回答用户的问题。

**注意事项**：
- 优先使用知识文档中的内容来回答
- 如果文档中没有直接答案，可以基于文档内容合理推断
- 如果完全没有相关文档，请诚实告知用户
- 回答要专业、准确、条理清晰
- 适当引用文档来源
- 如果用户有追问，结合对话历史回答

**检索到的知识文档**：
{context}

{history_section}"""),
            ("user", "用户问题：{question}")
        ])

        # 6. LLM 生成回答
        try:
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke({
                "context": context,
                "history_section": history_context,
                "question": rewritten_query
            })

            answer = response.content if hasattr(response, 'content') else response
        except Exception as e:
            logger.error(f"❌ LLM 生成回答失败: {str(e)}")
            answer = f"抱歉，生成回答时出错: {str(e)}"

        # 7. 构建返回结果
        sources = [
            {
                "title": d["title"],
                "content": d["content"][:200] + "..." if len(d["content"]) > 200 else d["content"],
                "similarity": d["similarity"]
            }
            for d in docs
        ]

        return {
            "answer": answer,
            "sources": sources,
            "has_context": len(docs) > 0,
            "rewritten_query": rewritten_query if rewritten_query != query else None
        }

    def get_doc_count(self) -> int:
        """获取知识库文档总数"""
        session = self.Session()
        try:
            result = session.execute(
                text("SELECT COUNT(*) FROM knowledge_docs WHERE embedding IS NOT NULL")
            )
            return result.scalar() or 0
        finally:
            session.close()


# 全局服务实例
rag_service = RAGService()
