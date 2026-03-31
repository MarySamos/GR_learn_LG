"""
Z-Rop FastAPI Application Entry Point
银行营销数据分析系统后端入口
"""
import logging
import traceback
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.api_v1 import api_router

# Development origins for CORS
_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
]

# Error log file
_ERROR_LOG_FILE = Path("logs") / "error.log"


def setup_logging() -> None:
    """Configure application logging with file and console handlers."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO if settings.DEBUG else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    # 专门记录错误的 logger
    error_logger = logging.getLogger("error")
    error_logger.setLevel(logging.ERROR)
    error_handler = logging.FileHandler(_ERROR_LOG_FILE, encoding="utf-8")
    error_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d"
    ))
    error_logger.addHandler(error_handler)


def log_error(request: Request, exc: Exception) -> None:
    """记录错误到文件"""
    error_logger = logging.getLogger("error")

    error_info = f"""
============================================
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
请求: {request.method} {request.url.path}
客户端: {request.client.host if request.client else 'unknown'}
异常类型: {type(exc).__name__}
异常消息: {str(exc)}
============================================
堆栈跟踪:
{traceback.format_exc()}
============================================
"""
    error_logger.error(error_info)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered bank marketing data analysis system",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS - always enabled for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 开发环境允许所有来源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局异常处理器
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """捕获所有未处理的异常"""
        log_error(request, exc)

        # 同时打印到控制台
        print(f"\n{'='*60}")
        print(f"ERROR: {type(exc).__name__}: {str(exc)}")
        print(f"{'='*60}")
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "detail": f"服务器内部错误: {str(exc)}",
                "type": type(exc).__name__,
            },
        )

    app.include_router(api_router)
    return app


# Initialize logging and create app
setup_logging()
app = create_app()


@app.get("/")
def root():
    """Root endpoint - Welcome page."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/logs/error")
def get_error_logs():
    """获取最近的错误日志（仅开发环境）"""
    if not settings.DEBUG:
        return {"error": "仅开发环境可用"}

    try:
        if _ERROR_LOG_FILE.exists():
            with open(_ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            # 返回最后 5000 字符
            return {"logs": content[-5000:]}
        return {"logs": "暂无错误日志"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
