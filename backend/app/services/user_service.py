"""用户认证服务.

处理用户注册、登录、JWT 生成和验证

使用 bcrypt 进行密码哈希，JWT 进行身份认证
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from bcrypt import checkpw, gensalt, hashpw
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User

# User role constants
_ROLE_USER = "user"

# Default user values
_DEFAULT_DEPARTMENT = None
_DEFAULT_ROLE = _ROLE_USER

# bcrypt 配置
_BCRYPT_ROUNDS = 12  # 哈希轮数，每增加1轮计算时间翻倍，12是推荐值


# ========== Password Functions ==========

def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码.

    Args:
        password: 明文密码

    Returns:
        哈希后的密码字符串

    Note:
        - 自动生成盐值并包含在哈希结果中
        - 使用 12 轮哈希，平衡安全性和性能
        - 每次哈希相同密码结果不同（因为盐值随机）
    """
    pwd_bytes = password.encode('utf-8')
    salt = gensalt(rounds=_BCRYPT_ROUNDS)
    hashed = hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码.

    Args:
        plain_password: 明文密码
        hashed_password: 数据库中存储的哈希密码

    Returns:
        密码是否匹配
    """
    pwd_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    return checkpw(pwd_bytes, hash_bytes)


# ========== JWT Functions ==========

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌.

    Args:
        data: 要编码的数据（通常是 user_id 或 employee_id）
        expires_delta: 过期时间增量

    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str, expected_type: Optional[str] = None) -> Optional[str]:
    """验证 JWT 令牌并返回用户 ID.

    Args:
        token: JWT token 字符串

    Returns:
        用户工号（employee_id）如果验证成功，否则返回 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")

        # Backward compatibility: legacy access tokens may not include token type.
        if expected_type == "access":
            if token_type not in (None, "access"):
                return None
        elif expected_type and token_type != expected_type:
            return None

        employee_id: str = payload.get("sub")
        return employee_id if employee_id else None
    except JWTError:
        return None


def create_refresh_token(data: dict) -> str:
    """创建 JWT 刷新令牌（有效期更长）.

    Args:
        data: 要编码的数据

    Returns:
        JWT refresh token 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)  # 7天有效期
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ========== User Functions ==========

def authenticate_user(db: Session, employee_id: str, password: str) -> Optional[User]:
    """验证用户凭据.

    Args:
        db: 数据库会话
        employee_id: 用户工号
        password: 密码

    Returns:
        User 对象如果验证成功，否则返回 None
    """
    user = db.query(User).filter(User.employee_id == employee_id).first()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user


def create_user(
    db: Session,
    employee_id: str,
    name: str,
    password: str,
    department: Optional[str] = _DEFAULT_DEPARTMENT,
    role: str = _DEFAULT_ROLE,
) -> User:
    """创建新用户.

    Args:
        db: 数据库会话
        employee_id: 工号
        name: 姓名
        password: 密码（明文）
        department: 部门
        role: 角色（user/admin/analyst）

    Returns:
        创建的 User 对象
    """
    hashed_pwd = hash_password(password)

    db_user = User(
        employee_id=employee_id,
        name=name,
        department=department,
        hashed_password=hashed_pwd,
        role=role,
        is_active=True
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def update_user_password(db: Session, user: User, new_password: str) -> User:
    """更新用户密码.

    Args:
        db: 数据库会话
        user: 用户对象
        new_password: 新密码（明文）

    Returns:
        更新后的 User 对象
    """
    user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_employee_id(db: Session, employee_id: str) -> Optional[User]:
    """根据工号获取用户"""
    return db.query(User).filter(User.employee_id == employee_id).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """根据 ID 获取用户"""
    return db.query(User).filter(User.id == user_id).first()
