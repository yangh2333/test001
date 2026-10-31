"""认证路由。"""
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import verify_password, create_token
from app.core.deps import get_current_user, get_user_roles
from app.core.errors import BizError, ERR, ok
from app.models.identity import User, Role, RoleBinding

router = APIRouter()


class LoginReq(BaseModel):
    employee_no: str
    password: str


class LoginResp(BaseModel):
    token: str
    user: dict


@router.post("/auth/login")
def login(req: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.employee_no == req.employee_no,
        User.deleted_at.is_(None),
    ).first()
    if not user:
        raise BizError(ERR["NOT_FOUND"], "工号不存在")
    if user.status != "active":
        raise BizError(ERR["FORBIDDEN"], "账号已停用")
    if not user.password_hash or not verify_password(req.password, user.password_hash):
        raise BizError(ERR["UNAUTHORIZED"], "密码错误")
    user.last_login_at = datetime.now()
    db.commit()
    roles = get_user_roles(user.id, db)
    token = create_token(user.id, user.employee_no, user.name, roles)
    return ok({
        "token": token,
        "user": {
            "id": user.id, "employee_no": user.employee_no, "name": user.name,
            "email": user.email, "dept_id": user.dept_id, "title": user.title,
            "roles": roles,
        },
    })


@router.get("/auth/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    roles = get_user_roles(user.id, db)
    return ok({
        "id": user.id, "employee_no": user.employee_no, "name": user.name,
        "email": user.email, "dept_id": user.dept_id, "title": user.title,
        "avatar_url": user.avatar_url, "roles": roles,
    })


@router.post("/auth/logout")
def logout():
    return ok({"message": "已退出"})
