"""依赖注入：当前用户、数据库会话、权限校验。"""
from fastapi import Depends, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.core.db import get_db
from app.core.security import decode_token
from app.core.errors import BizError, ERR
from app.models.identity import User
from app.models.identity import RoleBinding, Role


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise BizError(ERR["UNAUTHORIZED"], "未登录或令牌缺失")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise BizError(ERR["UNAUTHORIZED"], "令牌无效或已过期")
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user or user.status != "active":
        raise BizError(ERR["UNAUTHORIZED"], "账号不存在或已停用")
    return user


def require_roles(*role_codes: str):
    """要求用户拥有指定角色之一（全局角色）。"""

    def checker(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        user_roles = (
            db.query(Role.code)
            .join(RoleBinding, RoleBinding.role_id == Role.id)
            .filter(
                RoleBinding.user_id == user.id,
                RoleBinding.deleted_at.is_(None),
            )
            .all()
        )
        codes = {r[0] for r in user_roles}
        if not (set(role_codes) & codes):
            raise BizError(ERR["FORBIDDEN"], f"需要角色: {', '.join(role_codes)}")
        return user

    return checker


def get_user_roles(user_id: int, db: Session) -> list[str]:
    rows = (
        db.query(Role.code)
        .join(RoleBinding, RoleBinding.role_id == Role.id)
        .filter(RoleBinding.user_id == user_id, RoleBinding.deleted_at.is_(None))
        .all()
    )
    return [r[0] for r in rows]
