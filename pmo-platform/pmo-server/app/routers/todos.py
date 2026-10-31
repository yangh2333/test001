"""统一待办路由（M6）。"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import BizError, ERR, ok
from app.models.identity import User
from app.models.collab import TodoItem

router = APIRouter()


@router.get("/todos")
def list_todos(
    kind: Optional[str] = None,
    status: str = "open",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(TodoItem).filter(TodoItem.user_id == user.id)
    if kind:
        query = query.filter(TodoItem.kind == kind)
    if status:
        query = query.filter(TodoItem.status == status)
    rows = query.order_by(TodoItem.priority_score.desc()).all()
    return ok([{
        "id": t.id, "kind": t.kind, "ref_type": t.ref_type, "ref_id": t.ref_id,
        "title": t.title, "due_at": str(t.due_at) if t.due_at else None,
        "status": t.status, "priority_score": float(t.priority_score),
        "created_at": str(t.created_at),
    } for t in rows])


@router.patch("/todos/{todo_id}")
def update_todo(todo_id: int, status: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(TodoItem).filter(TodoItem.id == todo_id, TodoItem.user_id == user.id).first()
    if not t:
        raise BizError(ERR["NOT_FOUND"], "待办不存在")
    t.status = status
    if status == "done":
        t.done_at = datetime.now()
    db.commit()
    return ok({"id": t.id})


@router.get("/todos/stats")
def todo_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(TodoItem).filter(TodoItem.user_id == user.id, TodoItem.status == "open").all()
    stats = {}
    for t in rows:
        stats[t.kind] = stats.get(t.kind, 0) + 1
    return ok({"total": len(rows), "by_kind": stats})
