-- Z-Rop 数据库初始化 SQL 脚本
-- 请在 PostgreSQL 中执行此脚本

-- 1. 创建数据库
CREATE DATABASE bank_agent;

-- 2. 连接到新数据库
\c bank_agent

-- 3. 启用 pgvector 扩展（用于 RAG 向量检索）
CREATE EXTENSION IF NOT EXISTS vector;

-- 4. 验证扩展
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- 5. 显示数据库信息
\database bank_agent
