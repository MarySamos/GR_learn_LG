"""Knowledge Base Management API Endpoints.

提供知识文档上传、向量化、列表、删除等接口
"""
import os
import traceback
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.db.models import KnowledgeDoc, User
from app.api.dependencies import get_current_user
from app.services.rag_service import rag_service

router = APIRouter()

# 文件存储目录
_KNOWLEDGE_BASE_DIR = Path("data/knowledge")
_KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)

# 支持的文件类型
_SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}

# 分块配置
_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 50


def _get_loader(file_path: str, file_type: str):
    """根据文件类型获取对应的文档加载器"""
    if file_type == ".pdf":
        return PyPDFLoader(file_path)
    else:  # .txt, .md
        return TextLoader(file_path, encoding="utf-8")


@router.get("/list")
async def get_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=10, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取知识文档列表（分页）"""
    try:
        with engine.connect() as conn:
            # 获取总数
            result = conn.execute(text("SELECT COUNT(*) FROM knowledge_docs"))
            total = result.fetchone()[0]

            # 获取分页数据
            offset = (page - 1) * page_size
            result = conn.execute(text("""
                SELECT id, title, file_path, file_type,
                       LENGTH(content) as content_length,
                       created_at, updated_at,
                       uploaded_by,
                       (embedding IS NOT NULL) as has_embedding
                FROM knowledge_docs
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """), {"limit": page_size, "offset": offset})

            rows = result.fetchall()
            columns = list(result.keys())

            documents = []
            for row in rows:
                doc = dict(zip(columns, row))
                documents.append(doc)

            total_pages = (total + page_size - 1) // page_size

            return {
                "data": documents,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取文档列表失败")


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
):
    """获取知识库统计信息"""
    try:
        with engine.connect() as conn:
            # 总文档数
            result = conn.execute(text("SELECT COUNT(*) FROM knowledge_docs"))
            total_docs = result.fetchone()[0]

            # 有向量的文档数
            result = conn.execute(text("SELECT COUNT(*) FROM knowledge_docs WHERE embedding IS NOT NULL"))
            indexed_docs = result.fetchone()[0]

            # 按类型统计
            result = conn.execute(text("""
                SELECT file_type, COUNT(*) as count
                FROM knowledge_docs
                GROUP BY file_type
            """))
            by_type = {row[0]: row[1] for row in result.fetchall()}

            return {
                "total_docs": total_docs,
                "indexed_docs": indexed_docs,
                "by_type": by_type,
            }

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个文档详情"""
    try:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        return {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "file_path": doc.file_path,
            "file_type": doc.file_type,
            "meta_data": doc.meta_data,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "has_embedding": doc.embedding is not None,
        }

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取文档详情失败")


@router.post("/upload")
async def upload_document(
    title: str = Query(..., description="文档标题"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文档并向量化

    支持的文件类型：PDF, TXT, MD

    流程：
    1. 保存文件到本地
    2. 提取文本内容
    3. 分块处理
    4. 向量化并存储到数据库
    """
    # 验证文件类型
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in _SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持的类型: {', '.join(_SUPPORTED_EXTENSIONS)}"
        )

    try:
        # 1. 保存文件
        safe_filename = f"{current_user.id}_{file.filename}"
        file_path = _KNOWLEDGE_BASE_DIR / safe_filename

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 2. 加载文档
        loader = _get_loader(str(file_path), file_ext)
        documents = loader.load()

        if not documents:
            raise HTTPException(status_code=400, detail="无法从文件中提取内容")

        # 合并所有页面的内容
        full_text = "\n\n".join([doc.page_content for doc in documents])

        # 3. 文本分块
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=_CHUNK_SIZE,
            chunk_overlap=_CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
        chunks = text_splitter.split_text(full_text)

        # 4. 向量化（使用每个chunk分别向量化，取平均）
        import numpy as np

        embeddings = []
        for chunk in chunks:
            emb = rag_service.embed_query(chunk)
            embeddings.append(emb)

        # 计算平均向量作为文档向量
        avg_embedding = np.mean(embeddings, axis=0).tolist()

        # 5. 存储到数据库
        doc = KnowledgeDoc(
            title=title,
            content=full_text,
            file_path=str(file_path),
            file_type=file_ext[1:],  # 去掉点
            embedding=avg_embedding,
            meta_data={
                "chunk_count": len(chunks),
                "original_filename": file.filename,
                "file_size": len(content)
            },
            uploaded_by=current_user.id
        )

        db.add(doc)
        db.commit()
        db.refresh(doc)

        return {
            "message": "文档上传成功",
            "document": {
                "id": doc.id,
                "title": doc.title,
                "file_type": doc.file_type,
                "chunk_count": len(chunks),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        # 清理可能已保存的文件
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除知识文档"""
    try:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 只有管理员或上传者可以删除
        if current_user.role != "admin" and doc.uploaded_by != current_user.id:
            raise HTTPException(status_code=403, detail="无权限删除此文档")

        # 删除文件
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        # 删除数据库记录
        db.delete(doc)
        db.commit()

        return {"message": "文档删除成功"}

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="删除文档失败")


@router.post("/reindex/{doc_id}")
async def reindex_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新向量化文档（用于更新向量）"""
    try:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 文本分块
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=_CHUNK_SIZE,
            chunk_overlap=_CHUNK_OVERLAP
        )
        chunks = text_splitter.split_text(doc.content)

        # 向量化
        import numpy as np

        embeddings = []
        for chunk in chunks:
            emb = rag_service.embed_query(chunk)
            embeddings.append(emb)

        avg_embedding = np.mean(embeddings, axis=0).tolist()

        # 更新数据库
        doc.embedding = avg_embedding
        doc.meta_data = {
            **(doc.meta_data or {}),
            "chunk_count": len(chunks),
            "reindexed": True
        }
        db.commit()

        return {
            "message": "文档重新向量化成功",
            "chunk_count": len(chunks)
        }

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="重新向量化失败")
