"""会议与决议路由（M6）。"""
from datetime import datetime, date
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import BizError, ERR, ok
from app.models.identity import User
from app.models.collab import Meeting, MeetingDecision, TodoItem

router = APIRouter()


class MeetingCreate(BaseModel):
    title: str
    start_at: str
    project_id: Optional[int] = None
    attendees: Optional[List[int]] = None
    minutes_url: Optional[str] = None


class DecisionCreate(BaseModel):
    content: str
    owner_user_id: int
    due_date: str


@router.post("/meetings")
def create_meeting(req: MeetingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = Meeting(
        title=req.title, start_at=datetime.fromisoformat(req.start_at),
        project_id=req.project_id, attendees=req.attendees,
        minutes_url=req.minutes_url, created_by=user.id,
    )
    db.add(m)
    db.commit()
    return ok({"id": m.id})


@router.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    m = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not m:
        raise BizError(ERR["NOT_FOUND"], "会议不存在")
    decisions = db.query(MeetingDecision).filter(
        MeetingDecision.meeting_id == meeting_id, MeetingDecision.deleted_at.is_(None)
    ).all()
    return ok({
        "id": m.id, "title": m.title, "start_at": str(m.start_at),
        "project_id": m.project_id, "attendees": m.attendees,
        "minutes_url": m.minutes_url,
        "decisions": [{
            "id": d.id, "content": d.content, "owner_user_id": d.owner_user_id,
            "due_date": str(d.due_date), "status": d.status,
        } for d in decisions],
    })


@router.post("/meetings/{meeting_id}/decisions")
def add_decision(meeting_id: int, req: DecisionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = MeetingDecision(
        meeting_id=meeting_id, content=req.content,
        owner_user_id=req.owner_user_id,
        due_date=date.fromisoformat(req.due_date),
    )
    db.add(d)
    db.flush()
    # 自动生成待办给 owner
    due_at = datetime.fromisoformat(req.due_date)
    todo = TodoItem(
        user_id=req.owner_user_id, kind="meeting", ref_type="meeting_decision",
        ref_id=d.id, title=f"会议决议: {req.content[:50]}",
        due_at=due_at, priority_score=60,
    )
    db.add(todo)
    db.flush()
    d.todo_id = todo.id
    db.commit()
    return ok({"id": d.id, "todo_id": todo.id})


@router.get("/projects/{project_id}/meetings")
def list_meetings(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Meeting).filter(
        Meeting.project_id == project_id, Meeting.deleted_at.is_(None)
    ).order_by(Meeting.start_at.desc()).all()
    return ok([{
        "id": m.id, "title": m.title, "start_at": str(m.start_at),
    } for m in rows])
