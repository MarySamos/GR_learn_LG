"""用户认证相关接口.

包括：注册、登录、刷新令牌、修改密码、获取当前用户信息

使用 bcrypt 进行密码哈希，JWT 进行身份认证
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.db.models import User
from app.schemas.user import (
    PasswordUpdateRequest,
    RefreshTokenRequest,
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.user_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    get_user_by_employee_id,
    update_user_password,
    verify_password,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["认证"])

# Default role
_DEFAULT_ROLE = "user"


# ========== 首次运行初始化 ==========

@router.get("/first-run")
async def check_first_run(db: Session = Depends(get_db)):
    """检查是否为首次运行（数据库中没有用户）"""
    user_count = db.query(User).count()
    return {
        "is_first_run": user_count == 0,
        "user_count": user_count
    }


@router.post("/init-admin")
async def init_first_admin(
    employee_id: str,
    name: str,
    password: str,
    department: str = "IT部门",
    db: Session = Depends(get_db),
):
    """首次运行时创建超级管理员（无需认证）"""
    # 检查是否已有用户
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统已初始化，请使用正常登录流程"
        )

    # 验证输入
    if not employee_id or not name or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="工号、姓名和密码不能为空"
        )

    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码至少6位"
        )

    # 创建超级管理员
    from app.services.user_service import hash_password
    admin_user = User(
        employee_id=employee_id,
        name=name,
        department=department,
        hashed_password=hash_password(password),
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    return {
        "message": "超级管理员创建成功",
        "user": {
            "id": admin_user.id,
            "employee_id": admin_user.employee_id,
            "name": admin_user.name,
            "role": admin_user.role
        }
    }


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册接口.

    Args:
        user_data: 用户注册信息（工号、姓名、密码、部门）
        db: 数据库会话

    Returns:
        Token 响应（包含 access_token、refresh_token 和用户信息）

    Raises:
        HTTPException 400: 用户已存在或数据验证失败
        HTTPException 500: 数据库错误
    """
    try:
        existing_user = get_user_by_employee_id(db, employee_id=user_data.employee_id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该工号已被注册",
            )

        new_user = create_user(
            db=db,
            employee_id=user_data.employee_id,
            name=user_data.name,
            password=user_data.password,
            department=user_data.department,
            # Public registration always creates least-privileged users.
            role=_DEFAULT_ROLE,
        )

        access_token = create_access_token(data={"sub": new_user.employee_id})
        refresh_token = create_refresh_token(data={"sub": new_user.employee_id})

        # 直接构造 UserResponse，避免 model_validate 问题
        user_response = UserResponse(
            id=new_user.id,
            employee_id=new_user.employee_id,
            name=new_user.name,
            department=new_user.department,
            role=new_user.role,
            is_active=new_user.is_active,
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}",
        )


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录接口.

    Args:
        user_data: 用户登录信息（工号、密码）
        db: 数据库会话

    Returns:
        Token 响应（包含 access_token、refresh_token 和用户信息）

    Raises:
        HTTPException 401: 工号或密码错误
        HTTPException 500: 服务器错误
    """
    user = authenticate_user(
        db=db,
        employee_id=user_data.employee_id,
        password=user_data.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="工号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.employee_id})
    refresh_token = create_refresh_token(data={"sub": user.employee_id})

    from app.services.log_service import log_service

    log_service.log_action(
        db=db,
        user_id=user.id,
        action="login",
        resource="auth",
        details=f"用户 {user.name} 登录成功",
        status="success",
    )

    user_response = UserResponse(
        id=user.id,
        employee_id=user.employee_id,
        name=user.name,
        department=user.department,
        role=user.role,
        is_active=user.is_active,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response,
    )


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """刷新访问令牌.

    Args:
        request: 包含 refresh_token 的请求
        db: 数据库会话

    Returns:
        新的 Token 响应

    Raises:
        HTTPException 401: 刷新令牌无效
    """
    employee_id = verify_token(request.refresh_token, expected_type="refresh")

    if employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_employee_id(db, employee_id=employee_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
        )

    access_token = create_access_token(data={"sub": user.employee_id})
    new_refresh_token = create_refresh_token(data={"sub": user.employee_id})

    user_response = UserResponse(
        id=user.id,
        employee_id=user.employee_id,
        name=user.name,
        department=user.department,
        role=user.role,
        is_active=user.is_active,
    )

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response,
    )


@router.post("/change-password", response_model=dict)
def change_password(
    password_data: PasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改当前用户密码.

    Args:
        password_data: 包含旧密码和新密码的请求
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        成功消息

    Raises:
        HTTPException 400: 旧密码错误
        HTTPException 500: 服务器错误
    """
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误",
        )

    try:
        update_user_password(db, current_user, password_data.new_password)

        from app.services.log_service import log_service

        log_service.log_action(
            db=db,
            user_id=current_user.id,
            action="change_password",
            resource="auth",
            details="用户修改密码成功",
            status="success",
        )

        return {"message": "密码修改成功"}

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码修改失败，请稍后重试",
        )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息.

    Args:
        current_user: 当前登录用户（从 JWT token 解析）

    Returns:
        用户信息
    """
    return UserResponse(
        id=current_user.id,
        employee_id=current_user.employee_id,
        name=current_user.name,
        department=current_user.department,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.post("/logout", response_model=dict)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户登出（记录日志）.

    注意：JWT 是无状态的，客户端只需删除本地存储的 token 即可
    此接口主要用于记录登出日志

    Args:
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        成功消息
    """
    from app.services.log_service import log_service

    log_service.log_action(
        db=db,
        user_id=current_user.id,
        action="logout",
        resource="auth",
        details=f"用户 {current_user.name} 登出",
        status="success",
    )

    return {"message": "登出成功"}
