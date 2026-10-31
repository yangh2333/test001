"""周报路由（M6）。"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import BizError, ERR, ok
from app.models.identity import User
from app.models.collab import WeeklyReport
from app.models.task import Task
from app.models.project import Project

router = APIRouter()


def _week_range(d: date):
    """返回本周一和周日。"""
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


@router.get("/projects/{project_id}/weekly-reports")
def list_weekly(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(WeeklyReport).filter(
        WeeklyReport.project_id == project_id, WeeklyReport.deleted_at.is_(None)
    ).order_by(WeeklyReport.week_start.desc()).all()
    return ok([{
        "id": w.id, "week_start": str(w.week_start), "week_end": str(w.week_end),
        "status": w.status, "published_at": str(w.published_at) if w.published_at else None,
    } for w in rows])


@router.get("/projects/{project_id}/weekly-reports/current")
def current_weekly(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    monday, sunday = _week_range(date.today())
    w = db.query(WeeklyReport).filter(
        WeeklyReport.project_id == project_id,
        WeeklyReport.week_start == monday,
        WeeklyReport.deleted_at.is_(None),
    ).first()
    if not w:
        # 实时生成草稿
        tasks = db.query(Task).filter(
            Task.project_id == project_id, Task.deleted_at.is_(None)
        ).all()
        done_tasks = [{"id": t.id, "name": t.name} for t in tasks if t.status == "done"]
        in_progress = [{"id": t.id, "name": t.name, "progress": float(t.progress_pct)} for t in tasks if t.status == "in_progress"]
        next_week = [{"id": t.id, "name": t.name} for t in tasks if t.status in ("not_started", "in_progress")][:5]
        auto_content = {
            "done_tasks": done_tasks,
            "progress_delta": in_progress,
            "next_week": next_week,
            "need_decision": [],
        }
        w = WeeklyReport(
            project_id=project_id, week_start=monday, week_end=sunday,
            auto_content=auto_content, status="draft",
        )
        db.add(w)
        db.commit()
    return ok({
        "id": w.id, "week_start": str(w.week_start), "week_end": str(w.week_end),
        "auto_content": w.auto_content, "ai_summary": w.ai_summary,
        "pm_comment": w.pm_comment, "risk_supplement": w.risk_supplement,
        "status": w.status,
    })


@router.patch("/weekly-reports/{report_id}")
def update_weekly(report_id: int, pm_comment: str = "", risk_supplement: str = "", db: Session = Depends(get_db), _=Depends(get_current_user)):
    w = db.query(WeeklyReport).filter(WeeklyReport.id == report_id).first()
    if not w:
        raise BizError(ERR["NOT_FOUND"], "周报不存在")
    if pm_comment:
        w.pm_comment = pm_comment
    if risk_supplement:
        w.risk_supplement = risk_supplement
    db.commit()
    return ok({"id": w.id})


@router.post("/weekly-reports/{report_id}/publish")
def publish_weekly(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from datetime import datetime
    w = db.query(WeeklyReport).filter(WeeklyReport.id == report_id).first()
    if not w:
        raise BizError(ERR["NOT_FOUND"], "周报不存在")
    w.status = "published"
    w.published_at = datetime.now()
    w.published_by = user.id
    db.commit()
    return ok({"id": w.id, "status": "published"})
