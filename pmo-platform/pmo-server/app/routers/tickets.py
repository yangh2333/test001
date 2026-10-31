"""协同工单路由（M6）。"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import BizError, ERR, ok
from app.models.identity import User, Dept
from app.models.collab import Ticket, TicketAction
from app.models.project import Project

router = APIRouter()


class TicketCreate(BaseModel):
    title: str
    ticket_type: str  # resource/support/decision
    target_dept_id: int
    description: str
    project_id: Optional[int] = None
    target_user_id: Optional[int] = None
    priority: int = 3


@router.get("/tickets")
def list_tickets(
    scope: str = "all",  # all / mine / dept
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Ticket).filter(Ticket.deleted_at.is_(None))
    if scope == "mine":
        query = query.filter((Ticket.requester_user_id == user.id) | (Ticket.target_user_id == user.id))
    elif scope == "dept":
        query = query.filter(Ticket.target_dept_id == user.dept_id)
    if status:
        query = query.filter(Ticket.status == status)
    rows = query.order_by(Ticket.id.desc()).all()
    result = []
    for t in rows:
        req = db.query(User).filter(User.id == t.requester_user_id).first()
        dept = db.query(Dept).filter(Dept.id == t.target_dept_id).first()
        proj = db.query(Project).filter(Project.id == t.project_id).first() if t.project_id else None
        result.append({
            "id": t.id, "code": t.code, "title": t.title,
            "ticket_type": t.ticket_type, "priority": t.priority,
            "status": t.status, "sla_due_at": str(t.sla_due_at),
            "requester_user_id": t.requester_user_id,
            "requester_name": req.name if req else None,
            "target_dept_id": t.target_dept_id,
            "target_dept_name": dept.name if dept else None,
            "target_user_id": t.target_user_id,
            "project_id": t.project_id,
            "project_name": proj.name if proj else None,
            "escalate_level": t.escalate_level,
            "created_at": str(t.created_at),
        })
    return ok(result)


@router.post("/tickets")
def create_ticket(req: TicketCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ym = datetime.now().strftime("%Y%m%d")
    count = db.query(Ticket).filter(Ticket.code.like(f"TK-{ym}%")).count() + 1
    code = f"TK-{ym}-{count:04d}"
    # SLA: 1 个工作日（简化为 24 小时）
    sla = datetime.now() + timedelta(hours=24)
    t = Ticket(
        code=code, title=req.title, ticket_type=req.ticket_type,
        project_id=req.project_id, requester_user_id=user.id,
        target_dept_id=req.target_dept_id, target_user_id=req.target_user_id,
        description=req.description, priority=req.priority,
        status="pending", sla_due_at=sla,
    )
    db.add(t)
    db.flush()
    db.add(TicketAction(
        ticket_id=t.id, actor_user_id=user.id, action="create",
        from_status=None, to_status="pending",
    ))
    db.commit()
    return ok({"id": t.id, "code": code, "sla_due_at": str(sla)})


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not t:
        raise BizError(ERR["NOT_FOUND"], "工单不存在")
    data = {
        "id": t.id, "code": t.code, "title": t.title,
        "ticket_type": t.ticket_type, "priority": t.priority,
        "status": t.status, "description": t.description,
        "project_id": t.project_id, "requester_user_id": t.requester_user_id,
        "target_dept_id": t.target_dept_id, "target_user_id": t.target_user_id,
        "sla_due_at": str(t.sla_due_at), "responded_at": str(t.responded_at) if t.responded_at else None,
        "resolved_at": str(t.resolved_at) if t.resolved_at else None,
        "escalate_level": t.escalate_level,
        "satisfaction_score": t.satisfaction_score,
        "created_at": str(t.created_at),
    }
    actions = db.query(TicketAction).filter(TicketAction.ticket_id == ticket_id).order_by(TicketAction.created_at).all()
    data["actions"] = [{
        "action": a.action, "actor_user_id": a.actor_user_id,
        "from_status": a.from_status, "to_status": a.to_status,
        "comment": a.comment, "created_at": str(a.created_at),
    } for a in actions]
    return ok(data)


def _transition(db, t, action, new_status, actor_id, comment=None, **fields):
    old = t.status
    t.status = new_status
    for k, v in fields.items():
        setattr(t, k, v)
    db.add(TicketAction(
        ticket_id=t.id, actor_user_id=actor_id, action=action,
        from_status=old, to_status=new_status, comment=comment,
    ))


@router.post("/tickets/{ticket_id}/assign")
def assign(ticket_id: int, target_user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not t:
        raise BizError(ERR["NOT_FOUND"], "工单不存在")
    _transition(db, t, "assign", "accepted", user.id, target_user_id=target_user_id, responded_at=datetime.now())
    db.commit()
    return ok({"id": t.id, "status": t.status})


@router.post("/tickets/{ticket_id}/accept")
def accept(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not t:
        raise BizError(ERR["NOT_FOUND"], "工单不存在")
    _transition(db, t, "accept", "accepted", user.id, responded_at=datetime.now())
    db.commit()
    return ok({"id": t.id, "status": t.status})


@router.post("/tickets/{ticket_id}/resolve")
def resolve(ticket_id: int, comment: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not t:
        raise BizError(ERR["NOT_FOUND"], "工单不存在")
    _transition(db, t, "resolve", "resolved", user.id, comment=comment, resolved_at=datetime.now())
    db.commit()
    return ok({"id": t.id, "status": t.status})


@router.post("/tickets/{ticket_id}/close")
def close(ticket_id: int, satisfaction_score: int = 5, close_comment: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not t:
        raise BizError(ERR["NOT_FOUND"], "工单不存在")
    _transition(db, t, "close", "closed", user.id, comment=close_comment,
                satisfaction_score=satisfaction_score, closed_by=user.id)
    db.commit()
    return ok({"id": t.id, "status": t.status})


@router.post("/tickets/{ticket_id}/comment")
def comment(ticket_id: int, comment: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not t:
        raise BizError(ERR["NOT_FOUND"], "工单不存在")
    db.add(TicketAction(ticket_id=t.id, actor_user_id=user.id, action="comment", comment=comment))
    db.commit()
    return ok({"id": t.id})
