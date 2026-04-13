"""FastAPI Dependency Injection Functions.

JWT 验证和当前用户检索的依赖注入
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import User
from app.services.user_service import get_user_by_employee_id, verify_token

# Bearer token security scheme
security = HTTPBearer()

# Valid roles
_ADMIN_ROLE = "admin"
_ANALYST_ROLES = {"admin", "analyst"}

# Exception templates
_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT token 获取当前登录用户.

    Args:
        credentials: HTTP Authorization header 中的 Bearer 凭证
        db: 数据库会话

    Returns:
        当前登录的 User 对象

    Raises:
        HTTPException: 如果 token 无效或用户不存在
    """
    employee_id = verify_token(credentials.credentials, expected_type="access")
    if employee_id is None:
        raise _CREDENTIALS_EXCEPTION

    user = get_user_by_employee_id(db, employee_id=employee_id)
    if user is None:
        raise _CREDENTIALS_EXCEPTION

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求管理员角色.

    Args:
        current_user: 当前用户

    Returns:
        User 对象

    Raises:
        HTTPException: 如果用户不是管理员
    """
    if current_user.role != _ADMIN_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def require_analyst(current_user: User = Depends(get_current_user)) -> User:
    """要求分析师或管理员角色.

    Args:
        current_user: 当前用户

    Returns:
        User 对象

    Raises:
        HTTPException: 如果用户不是分析师或管理员
    """
    if current_user.role not in _ANALYST_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst privileges required",
        )
    return current_user
