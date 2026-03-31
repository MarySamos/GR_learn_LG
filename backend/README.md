# Z-Rop Backend

银行营销数据分析系统后端服务 - AI-powered bank marketing data analysis system

## 项目简介

基于 FastAPI + LangGraph 的智能银行营销数据分析系统，提供数据查询、分析、预测能力。

## 主要功能

- **用户认证**: JWT 认证和权限管理
- **智能对话**: 基于 LangGraph 的 AI 智能助手
- **数据管理**: 数据上传、查询、导出
- **数据分析**: 聚类分析、客户细分
- **预测服务**: 机器学习模型预测
- **仪表板**: KPI 和可视化数据

## 技术栈

- **框架**: FastAPI
- **AI**: LangGraph, LangChain, OpenAI
- **数据库**: SQLAlchemy (支持 SQLite/PostgreSQL/MySQL)
- **机器学习**: Scikit-learn
- **数据处理**: Pandas, NumPy

## 安装

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 配置

创建 `.env` 文件：

```env
# Application
APP_NAME=BankAgent-Pro
APP_VERSION=1.0.0
DEBUG=True

# Database
DATABASE_URL=sqlite:///./bank_agent.db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=your-openai-api-key
```

## 运行

```bash
# 启动服务器
python main.py

# 或使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问 API 文档: http://localhost:8000/docs

## API 端点

- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/chat` - AI 对话
- `GET /api/v1/dashboard` - 仪表板数据
- `POST /api/v1/predict` - 预测分析
- `POST /api/v1/analysis/clustering` - 聚类分析

## 项目结构

```
backend/
├── app/
│   ├── api/           # API 端点
│   ├── core/          # 核心配置
│   ├── db/            # 数据库模型和 CRUD
│   ├── graphs/        # LangGraph 工作流
│   ├── schemas/       # Pydantic 模型
│   └── services/      # 业务逻辑服务
├── logs/              # 日志文件
├── main.py            # 应用入口
└── requirements.txt   # 项目依赖
```

## 开发

```bash
# 运行测试
pytest

# 代码格式化
black .
isort .

# 类型检查
mypy app/
```

## License

MIT
