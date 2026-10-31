"""组织与人员路由。"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.db import get_db
from app.core.deps import get_current_user, get_user_roles
from app.core.errors import ok
from app.models.identity import User, Dept, Role, RoleBinding
from app.models.resource import Skill, MemberSkill

router = APIRouter()


def _user_dict(u: User, db: Session) -> dict:
    dept = db.query(Dept).filter(Dept.id == u.dept_id).first()
    roles = get_user_roles(u.id, db)
    return {
        "id": u.id, "employee_no": u.employee_no, "name": u.name,
        "email": u.email, "dept_id": u.dept_id,
        "dept_name": dept.name if dept else None,
        "title": u.title, "status": u.status, "roles": roles,
        "avatar_url": u.avatar_url,
    }


@router.get("/depts")
def list_depts(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Dept).filter(Dept.deleted_at.is_(None)).order_by(Dept.order_no).all()
    return ok([{
        "id": d.id, "name": d.name, "parent_id": d.parent_id,
        "path": d.path, "manager_user_id": d.manager_user_id,
    } for d in rows])


@router.get("/users")
def list_users(
    q: Optional[str] = None,
    dept_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(User).filter(User.deleted_at.is_(None))
    if q:
        like = f"%{q}%"
        query = query.filter((User.name.like(like)) | (User.employee_no.like(like)))
    if dept_id:
        query = query.filter(User.dept_id == dept_id)
    rows = query.limit(200).all()
    return ok([_user_dict(u, db) for u in rows])


@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return ok(None)
    return ok(_user_dict(u, db))


@router.get("/skills")
def list_skills(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Skill).filter(Skill.deleted_at.is_(None), Skill.status == "active").all()
    return ok([{"id": s.id, "code": s.code, "name": s.name, "category": s.category} for s in rows])
