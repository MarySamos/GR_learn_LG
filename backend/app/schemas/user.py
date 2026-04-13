"""用户相关的 Pydantic 模型.

定义请求和响应的数据格式
"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserBase(BaseModel):
    """用户基础模型"""
    employee_id: str = Field(..., description="工号")
    name: str = Field(..., description="姓名")
    department: Optional[str] = Field(None, description="部门")


class UserCreate(UserBase):
    """用户注册请求模型"""
    password: str = Field(..., min_length=6, description="密码（至少6位）")

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度（基础验证）"""
        if len(v) < 6:
            raise ValueError("密码长度至少为6位")
        return v


class UserLogin(BaseModel):
    """用户登录请求模型"""
    employee_id: str = Field(..., description="工号")
    password: str = Field(..., description="密码")


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token 响应模型"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None  # 过期时间（秒）
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str


class TokenData(BaseModel):
    """Token 数据模型（用于解析 JWT）"""
    employee_id: Optional[str] = None


class PasswordUpdateRequest(BaseModel):
    """密码更新请求模型"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码（至少6位）")
