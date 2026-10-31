"""管理后台路由（M10）。"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles, get_user_roles
from app.core.security import hash_password
from app.core.errors import BizError, ERR, ok
from app.models.identity import User, Dept, Role, RoleBinding
from app.models.platform import Dictionary, AuditLog, IntegrationConfig
from app.models.project import Project

router = APIRouter()


# ---------------- 角色与授权 ----------------
@router.get("/admin/roles")
def list_roles(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Role).all()
    return ok([{"id": r.id, "code": r.code, "name": r.name, "scope": r.scope, "builtin": r.builtin} for r in rows])


@router.get("/admin/role-bindings")
def list_role_bindings(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    query = db.query(RoleBinding).filter(RoleBinding.deleted_at.is_(None))
    if user_id:
        query = query.filter(RoleBinding.user_id == user_id)
    rows = query.all()
    result = []
    for rb in rows:
        role = db.query(Role).filter(Role.id == rb.role_id).first()
        u = db.query(User).filter(User.id == rb.user_id).first()
        result.append({
            "id": rb.id, "user_id": rb.user_id, "user_name": u.name if u else None,
            "role_id": rb.role_id, "role_code": role.code if role else None,
            "role_name": role.name if role else None,
            "project_id": rb.project_id, "dept_id": rb.dept_id,
            "expires_at": str(rb.expires_at) if rb.expires_at else None,
        })
    return ok(result)


class RoleBindingCreate(BaseModel):
    user_id: int
    role_id: int
    project_id: Optional[int] = None
    dept_id: Optional[int] = None


@router.post("/admin/role-bindings")
def create_role_binding(req: RoleBindingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rb = RoleBinding(
        user_id=req.user_id, role_id=req.role_id,
        project_id=req.project_id, dept_id=req.dept_id,
        granted_by=user.id,
        expires_at=datetime.now() + timedelta(days=365),
    )
    db.add(rb)
    db.commit()
    return ok({"id": rb.id})


@router.delete("/admin/role-bindings/{binding_id}")
def delete_role_binding(binding_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rb = db.query(RoleBinding).filter(RoleBinding.id == binding_id).first()
    if rb:
        rb.deleted_at = datetime.now()
        db.commit()
    return ok({"id": binding_id})


# ---------------- 用户管理 ----------------
class UserCreate(BaseModel):
    employee_no: str
    name: str
    email: str
    dept_id: Optional[int] = None
    title: Optional[str] = None
    password: str = "123456"


@router.post("/admin/users")
def create_user(req: UserCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(User).filter(User.employee_no == req.employee_no).first():
        raise BizError(ERR["CONFLICT"], "工号已存在")
    u = User(
        employee_no=req.employee_no, name=req.name, email=req.email,
        dept_id=req.dept_id, title=req.title,
        status="active", password_hash=hash_password(req.password),
    )
    db.add(u)
    db.commit()
    return ok({"id": u.id})


@router.patch("/admin/users/{user_id}")
def update_user(user_id: int, status: Optional[str] = None, db: Session = Depends(get_db), _=Depends(get_current_user)):
    u = db.query(User).filter(User.id == user_id).first()
    if u and status:
        u.status = status
        db.commit()
    return ok({"id": user_id})


# ---------------- 部门管理 ----------------
@router.post("/admin/depts")
def create_dept(name: str, parent_id: Optional[int] = None, db: Session = Depends(get_db), _=Depends(get_current_user)):
    source_id = f"dept_{int(datetime.now().timestamp())}"
    parent = db.query(Dept).filter(Dept.id == parent_id).first() if parent_id else None
    path = f"{parent.path}{source_id}/" if parent else f"/{source_id}/"
    d = Dept(name=name, parent_id=parent_id, source_id=source_id, path=path, status="active")
    db.add(d)
    db.commit()
    return ok({"id": d.id})


# ---------------- 字典 ----------------
@router.get("/admin/dictionaries")
def list_dictionaries(category: Optional[str] = None, db: Session = Depends(get_db), _=Depends(get_current_user)):
    query = db.query(Dictionary).filter(Dictionary.deleted_at.is_(None))
    if category:
        query = query.filter(Dictionary.category == category)
    rows = query.all()
    return ok([{"id": d.id, "category": d.category, "code": d.code, "name": d.name, "sort_order": d.sort_order} for d in rows])


@router.post("/admin/dictionaries")
def create_dictionary(category: str, code: str, name: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    d = Dictionary(category=category, code=code, name=name)
    db.add(d)
    db.commit()
    return ok({"id": d.id})


# ---------------- 审计日志 ----------------
@router.get("/admin/audit-logs")
def list_audit_logs(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return ok([{
        "id": a.id, "action": a.action, "object_type": a.object_type,
        "object_id": a.object_id, "actor_user_id": a.actor_user_id,
        "actor_type": a.actor_type, "trace_id": a.trace_id,
        "created_at": str(a.created_at),
    } for a in rows])


# ---------------- 集成配置 ----------------
@router.get("/admin/integrations")
def list_integrations(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(IntegrationConfig).all()
    return ok([{
        "id": i.id, "code": i.code, "name": i.name, "enabled": i.enabled,
        "last_sync_at": str(i.last_sync_at) if i.last_sync_at else None,
        "last_status": i.last_status, "fail_count": i.fail_count,
    } for i in rows])
