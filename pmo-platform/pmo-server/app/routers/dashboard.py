"""驾驶舱与报表路由（M8）。"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.db import get_db
from app.core.deps import get_current_user, get_user_roles
from app.core.errors import ok
from app.models.identity import User
from app.models.project import Project, Gate
from app.models.task import Task
from app.models.collab import Ticket, TodoItem
from app.models.resource import ResourcePool
from app.models.risk import Risk

router = APIRouter()


@router.get("/dashboard/pm")
def pm_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 我的项目
    projects = db.query(Project).filter(
        Project.pm_user_id == user.id, Project.deleted_at.is_(None)
    ).all()
    project_ids = [p.id for p in projects]

    health_dist = {"green": 0, "yellow": 0, "red": 0, "na": 0}
    for p in projects:
        health_dist[p.health] = health_dist.get(p.health, 0) + 1

    # 我的待办
    todos = db.query(TodoItem).filter(TodoItem.user_id == user.id, TodoItem.status == "open").count()

    # 我的阻塞任务
    blocked = db.query(Task).filter(
        Task.owner_user_id == user.id, Task.status == "blocked",
        Task.deleted_at.is_(None),
    ).count()

    # 我的超期工单
    now = datetime.now()
    overdue_tickets = db.query(Ticket).filter(
        Ticket.requester_user_id == user.id,
        Ticket.status.in_(["pending", "accepted"]),
        Ticket.sla_due_at < now,
        Ticket.deleted_at.is_(None),
    ).count()

    # 阻塞的 Gate
    blocked_gates = 0
    if project_ids:
        blocked_gates = db.query(Gate).filter(
            Gate.project_id.in_(project_ids), Gate.blocked_flag == True,
            Gate.deleted_at.is_(None),
        ).count()

    return ok({
        "projects_count": len(projects),
        "health_distribution": health_dist,
        "my_todos": todos,
        "blocked_tasks": blocked,
        "overdue_tickets": overdue_tickets,
        "blocked_gates": blocked_gates,
    })


@router.get("/dashboard/exec")
def exec_dashboard(db: Session = Depends(get_db), _=Depends(get_current_user)):
    projects = db.query(Project).filter(Project.deleted_at.is_(None)).all()
    health_dist = {"green": 0, "yellow": 0, "red": 0, "na": 0}
    for p in projects:
        health_dist[p.health] = health_dist.get(p.health, 0) + 1

    # 阻塞清单
    blocked_tasks = db.query(Task).filter(
        Task.status == "blocked", Task.deleted_at.is_(None)
    ).count()
    overdue_tickets = db.query(Ticket).filter(
        Ticket.status.in_(["pending", "accepted"]),
        Ticket.sla_due_at < datetime.now(),
        Ticket.deleted_at.is_(None),
    ).count()
    blocked_gates = db.query(Gate).filter(
        Gate.blocked_flag == True, Gate.deleted_at.is_(None)
    ).count()

    return ok({
        "total_projects": len(projects),
        "health_distribution": health_dist,
        "blocked_tasks": blocked_tasks,
        "overdue_tickets": overdue_tickets,
        "blocked_gates": blocked_gates,
    })


@router.get("/reports/blockers")
def blockers(db: Session = Depends(get_db), _=Depends(get_current_user)):
    blocked_tasks = db.query(Task).filter(
        Task.status == "blocked", Task.deleted_at.is_(None)
    ).all()
    overdue_tickets = db.query(Ticket).filter(
        Ticket.status.in_(["pending", "accepted"]),
        Ticket.sla_due_at < datetime.now(),
        Ticket.deleted_at.is_(None),
    ).all()
    return ok({
        "blocked_tasks": [{
            "id": t.id, "name": t.name, "project_id": t.project_id,
            "blocked_reason": t.blocked_reason,
        } for t in blocked_tasks],
        "overdue_tickets": [{
            "id": t.id, "code": t.code, "title": t.title,
            "sla_due_at": str(t.sla_due_at),
        } for t in overdue_tickets],
    })


@router.get("/reports/pending-decisions")
def pending_decisions(db: Session = Depends(get_db), _=Depends(get_current_user)):
    # 待决策：需要评审的 Gate + 待审批项目
    gates = db.query(Gate).filter(
        Gate.status.in_(["in_review", "material_ready"]),
        Gate.deleted_at.is_(None),
    ).all()
    return ok([{
        "id": g.id, "name": g.name, "status": g.status, "is_high_risk": g.is_high_risk,
    } for g in gates])
