"""Application Configuration Management.

从环境变量加载应用配置。
"""
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

# Root directory for .env file location (backend/app/core -> backend/app -> backend)
_ROOT_DIR = Path(__file__).parent.parent.parent

# JWT default values
_ALGORITHM_DEFAULT = "HS256"
_TOKEN_EXPIRE_MINUTES_DEFAULT = 30

# Checkpoint type constants
_CHECKPOINT_TYPE_MEMORY = "memory"
_CHECKPOINT_TYPE_POSTGRES = "postgres"

# LLM default values
_LLM_MODEL_DEFAULT = "glm-4"
_LLM_API_BASE_DEFAULT = "https://open.bigmodel.cn/api/paas/v4/"


class Settings(BaseSettings):
    """Application configuration settings."""

    # Basic Application Info
    APP_NAME: str = "Z-Rop"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database Configuration
    DATABASE_URL: str

    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = _ALGORITHM_DEFAULT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _TOKEN_EXPIRE_MINUTES_DEFAULT

    # OpenAI API Configuration
    OPENAI_API_KEY: str
    OPENAI_API_BASE: Optional[str] = None

    # Zhipu API Configuration
    ZHIPU_API_KEY: Optional[str] = None
    ZHIPU_BASE_URL: Optional[str] = None

    # LLM Configuration
    LLM_MODEL: str = _LLM_MODEL_DEFAULT
    LLM_API_BASE: str = _LLM_API_BASE_DEFAULT

    # LangSmith Configuration
    LANGSMITH_PROJECT: Optional[str] = None
    LANGSMITH_API_KEY: Optional[str] = None

    # Checkpoint Configuration
    CHECKPOINT_TYPE: str = _CHECKPOINT_TYPE_MEMORY
    CHECKPOINT_DB_URL: Optional[str] = None

    class Config:
        """Pydantic configuration."""
        env_file = _ROOT_DIR / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()
