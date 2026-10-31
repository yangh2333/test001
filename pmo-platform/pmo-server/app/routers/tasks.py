"""任务与 WBS 路由（M1）。"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import BizError, ERR, ok
from app.models.identity import User
from app.models.task import Wbs, Task, TaskRaci, Dependency
from app.models.project import Project

router = APIRouter()


class WbsCreate(BaseModel):
    project_id: int
    parent_id: Optional[int] = None
    code: str
    name: str
    level: int


class TaskCreate(BaseModel):
    project_id: int
    wbs_id: Optional[int] = None
    parent_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    owner_user_id: int
    plan_start: date
    plan_end: date
    est_hours: Optional[float] = None
    priority: int = 3
    is_milestone: bool = False
    assignee_ids: Optional[List[int]] = None


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    progress_pct: Optional[float] = None
    plan_start: Optional[date] = None
    plan_end: Optional[date] = None
    owner_user_id: Optional[int] = None
    priority: Optional[int] = None
    blocked_reason: Optional[str] = None
    blocked_help_user_id: Optional[int] = None


class DepCreate(BaseModel):
    predecessor_task_id: int
    successor_task_id: int
    dep_type: str = "FS"
    lag_days: int = 0


def _task_dict(t: Task, db: Session) -> dict:
    owner = db.query(User).filter(User.id == t.owner_user_id).first()
    return {
        "id": t.id, "project_id": t.project_id, "wbs_id": t.wbs_id,
        "parent_id": t.parent_id, "name": t.name, "description": t.description,
        "owner_user_id": t.owner_user_id,
        "owner_name": owner.name if owner else None,
        "assignee_ids": t.assignee_ids or [],
        "plan_start": str(t.plan_start), "plan_end": str(t.plan_end),
        "actual_start": str(t.actual_start) if t.actual_start else None,
        "actual_end": str(t.actual_end) if t.actual_end else None,
        "est_hours": float(t.est_hours) if t.est_hours else None,
        "progress_pct": float(t.progress_pct or 0),
        "status": t.status, "priority": t.priority,
        "is_milestone": t.is_milestone, "is_critical": t.is_critical,
        "blocked_reason": t.blocked_reason,
        "ci_status": t.ci_status, "ci_ref": t.ci_ref,
    }


# ---------------- WBS ----------------
@router.get("/projects/{project_id}/wbs")
def list_wbs(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Wbs).filter(
        Wbs.project_id == project_id, Wbs.deleted_at.is_(None)
    ).order_by(Wbs.level, Wbs.order_no).all()
    return ok([{
        "id": w.id, "project_id": w.project_id, "parent_id": w.parent_id,
        "code": w.code, "name": w.name, "level": w.level, "order_no": w.order_no,
    } for w in rows])


@router.post("/projects/{project_id}/wbs")
def create_wbs(req: WbsCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if req.level > 4:
        raise BizError(ERR["BAD_REQUEST"], "WBS 最多 4 级")
    w = Wbs(**req.model_dump())
    db.add(w)
    db.commit()
    return ok({"id": w.id})


# ---------------- Task ----------------
@router.get("/projects/{project_id}/tasks")
def list_tasks(
    project_id: int,
    status: Optional[str] = None,
    owner_user_id: Optional[int] = None,
    wbs_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(Task).filter(Task.project_id == project_id, Task.deleted_at.is_(None))
    if status:
        query = query.filter(Task.status == status)
    if owner_user_id:
        query = query.filter(Task.owner_user_id == owner_user_id)
    if wbs_id:
        query = query.filter(Task.wbs_id == wbs_id)
    rows = query.order_by(Task.id).all()
    return ok([_task_dict(t, db) for t in rows])


@router.post("/projects/{project_id}/tasks")
def create_task(req: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = Task(
        project_id=req.project_id, wbs_id=req.wbs_id, parent_id=req.parent_id,
        name=req.name, description=req.description, owner_user_id=req.owner_user_id,
        plan_start=req.plan_start, plan_end=req.plan_end,
        est_hours=req.est_hours, priority=req.priority, is_milestone=req.is_milestone,
        assignee_ids=req.assignee_ids, created_by=user.id,
    )
    db.add(t)
    db.flush()
    # 默认 RACI：owner 为 A
    db.add(TaskRaci(task_id=t.id, user_id=req.owner_user_id, raci="A", is_primary_accountable=True))
    db.commit()
    return ok({"id": t.id})


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise BizError(ERR["NOT_FOUND"], "任务不存在")
    data = _task_dict(t, db)
    raci = db.query(TaskRaci).filter(TaskRaci.task_id == task_id, TaskRaci.deleted_at.is_(None)).all()
    data["raci"] = [{"user_id": r.user_id, "raci": r.raci, "is_primary_accountable": r.is_primary_accountable} for r in raci]
    # 依赖
    preds = db.query(Dependency).filter(Dependency.successor_task_id == task_id, Dependency.deleted_at.is_(None)).all()
    succs = db.query(Dependency).filter(Dependency.predecessor_task_id == task_id, Dependency.deleted_at.is_(None)).all()
    data["dependencies"] = {
        "predecessors": [{"id": d.id, "predecessor_task_id": d.predecessor_task_id, "dep_type": d.dep_type} for d in preds],
        "successors": [{"id": d.id, "successor_task_id": d.successor_task_id, "dep_type": d.dep_type} for d in succs],
    }
    return ok(data)


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, req: TaskUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise BizError(ERR["NOT_FOUND"], "任务不存在")
    data = req.model_dump(exclude_unset=True)
    if "status" in data and data["status"] == "blocked":
        if not data.get("blocked_reason") or not data.get("blocked_help_user_id"):
            raise BizError(ERR["BAD_REQUEST"], "标记阻塞必须填写阻塞原因和求助对象")
    for k, v in data.items():
        setattr(t, k, v)
    db.commit()
    return ok({"id": t.id})


# ---------------- Dependency ----------------
@router.get("/projects/{project_id}/dependencies")
def list_deps(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    task_ids = [t[0] for t in db.query(Task.id).filter(Task.project_id == project_id).all()]
    rows = db.query(Dependency).filter(
        Dependency.predecessor_task_id.in_(task_ids),
        Dependency.deleted_at.is_(None),
    ).all()
    return ok([{
        "id": d.id, "predecessor_task_id": d.predecessor_task_id,
        "successor_task_id": d.successor_task_id,
        "dep_type": d.dep_type, "lag_days": d.lag_days,
    } for d in rows])


@router.post("/projects/{project_id}/dependencies")
def create_dep(req: DepCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    # 简单成环检测
    if req.predecessor_task_id == req.successor_task_id:
        raise BizError(ERR["CONFLICT"], "不能依赖自己")
    existing = db.query(Dependency).filter(
        Dependency.predecessor_task_id == req.predecessor_task_id,
        Dependency.successor_task_id == req.successor_task_id,
        Dependency.deleted_at.is_(None),
    ).first()
    if existing:
        raise BizError(ERR["CONFLICT"], "依赖已存在")
    d = Dependency(**req.model_dump())
    db.add(d)
    db.commit()
    return ok({"id": d.id})


@router.delete("/dependencies/{dep_id}")
def delete_dep(dep_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    d = db.query(Dependency).filter(Dependency.id == dep_id).first()
    if d:
        db.delete(d)
        db.commit()
    return ok({"id": dep_id})
