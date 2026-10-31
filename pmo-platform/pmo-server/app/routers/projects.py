"""项目管理路由（M1）。"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.db import get_db
from app.core.deps import get_current_user, get_user_roles
from app.core.errors import BizError, ERR, ok
from app.models.identity import User, Dept
from app.models.project import (
    Project, ProjectType, Program, ProjectStakeholder,
    ProjectStage, StageTemplate, GateTemplate, Gate,
)
from app.models.task import Wbs, Task

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    type_id: int
    pm_user_id: int
    dept_id: int
    secrecy_level: str = "internal"
    plan_start: date
    plan_end: date
    program_id: Optional[int] = None
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    secrecy_level: Optional[str] = None
    plan_start: Optional[date] = None
    plan_end: Optional[date] = None
    pm_user_id: Optional[int] = None


def _project_dict(p: Project, db: Session) -> dict:
    pt = db.query(ProjectType).filter(ProjectType.id == p.type_id).first()
    pm = db.query(User).filter(User.id == p.pm_user_id).first()
    dept = db.query(Dept).filter(Dept.id == p.dept_id).first()
    pgm = db.query(Program).filter(Program.id == p.program_id).first() if p.program_id else None
    return {
        "id": p.id, "code": p.code, "name": p.name,
        "type_id": p.type_id, "type_name": pt.name if pt else None,
        "program_id": p.program_id, "program_name": pgm.name if pgm else None,
        "pm_user_id": p.pm_user_id, "pm_name": pm.name if pm else None,
        "dept_id": p.dept_id, "dept_name": dept.name if dept else None,
        "status": p.status, "secrecy_level": p.secrecy_level,
        "progress_pct": float(p.progress_pct or 0),
        "health": p.health,
        "plan_start": str(p.plan_start), "plan_end": str(p.plan_end),
        "actual_start": str(p.actual_start) if p.actual_start else None,
        "actual_end": str(p.actual_end) if p.actual_end else None,
        "data_pedigree": p.data_pedigree,
    }


@router.get("/project-types")
def list_project_types(db: Session = Depends(get_db), _=Depends(get_current_user)):
    types = db.query(ProjectType).filter(ProjectType.enabled == True).order_by(ProjectType.sort_order).all()
    result = []
    for t in types:
        stages = db.query(StageTemplate).filter(
            StageTemplate.type_id == t.id, StageTemplate.deleted_at.is_(None)
        ).order_by(StageTemplate.order_no).all()
        gates = db.query(GateTemplate).filter(
            GateTemplate.type_id == t.id, GateTemplate.deleted_at.is_(None)
        ).order_by(GateTemplate.order_no).all()
        result.append({
            "id": t.id, "code": t.code, "name": t.name,
            "stages": [{"id": s.id, "code": s.code, "name": s.name, "order_no": s.order_no, "is_core": s.is_core} for s in stages],
            "gates": [{"id": g.id, "code": g.code, "name": g.name, "order_no": g.order_no, "is_core": g.is_core, "is_high_risk": g.is_high_risk} for g in gates],
        })
    return ok(result)


@router.get("/projects")
def list_projects(
    status: Optional[str] = None,
    type_id: Optional[int] = None,
    pm_user_id: Optional[int] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(Project).filter(Project.deleted_at.is_(None))
    if status:
        query = query.filter(Project.status == status)
    if type_id:
        query = query.filter(Project.type_id == type_id)
    if pm_user_id:
        query = query.filter(Project.pm_user_id == pm_user_id)
    if q:
        query = query.filter(Project.name.like(f"%{q}%"))
    rows = query.order_by(Project.id.desc()).all()
    return ok([_project_dict(p, db) for p in rows])


@router.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not p:
        raise BizError(ERR["NOT_FOUND"], "项目不存在")
    data = _project_dict(p, db)
    # 阶段
    stages = db.query(ProjectStage).filter(
        ProjectStage.project_id == project_id, ProjectStage.deleted_at.is_(None)
    ).order_by(ProjectStage.order_no).all()
    data["stages"] = [{
        "id": s.id, "name": s.name, "order_no": s.order_no, "status": s.status,
        "plan_start": str(s.plan_start) if s.plan_start else None,
        "plan_end": str(s.plan_end) if s.plan_end else None,
    } for s in stages]
    # 门禁
    gates = db.query(Gate).filter(Gate.project_id == project_id, Gate.deleted_at.is_(None)).all()
    data["gates"] = [{
        "id": g.id, "name": g.name, "status": g.status, "decision": g.decision,
        "is_high_risk": g.is_high_risk, "blocked_flag": g.blocked_flag,
    } for g in gates]
    return ok(data)


@router.post("/projects")
def create_project(req: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 生成编号
    ym = datetime.now().strftime("%Y%m")
    pt = db.query(ProjectType).filter(ProjectType.id == req.type_id).first()
    if not pt:
        raise BizError(ERR["NOT_FOUND"], "项目类型不存在")
    prefix = f"PRJ-{pt.code.upper()[:4]}-{ym}"
    count = db.query(Project).filter(Project.code.like(f"{prefix}%")).count() + 1
    code = f"{prefix}-{count:03d}"

    proj = Project(
        code=code, name=req.name, type_id=req.type_id,
        pm_user_id=req.pm_user_id, dept_id=req.dept_id,
        status="draft", secrecy_level=req.secrecy_level,
        plan_start=req.plan_start, plan_end=req.plan_end,
        program_id=req.program_id, created_by=user.id,
    )
    db.add(proj)
    db.flush()

    # 实例化阶段与门禁
    stages = db.query(StageTemplate).filter(
        StageTemplate.type_id == req.type_id, StageTemplate.deleted_at.is_(None)
    ).order_by(StageTemplate.order_no).all()
    stage_map = {}
    for st in stages:
        ps = ProjectStage(
            project_id=proj.id, template_id=st.id, name=st.name,
            order_no=st.order_no, status="not_started",
        )
        db.add(ps)
        stage_map[st.id] = ps
    db.flush()

    gates = db.query(GateTemplate).filter(
        GateTemplate.type_id == req.type_id, GateTemplate.deleted_at.is_(None)
    ).order_by(GateTemplate.order_no).all()
    for gt in gates:
        ps = stage_map.get(gt.stage_template_id)
        g = Gate(
            project_id=proj.id,
            stage_id=ps.id if ps else None,
            template_id=gt.id, name=gt.name,
            is_high_risk=gt.is_high_risk, enforce_mode=gt.enforce_mode,
            status="not_started",
        )
        db.add(g)
    db.commit()
    return ok({"id": proj.id, "code": code, "status": "draft"})


@router.patch("/projects/{project_id}")
def update_project(project_id: int, req: ProjectUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise BizError(ERR["NOT_FOUND"], "项目不存在")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return ok({"id": p.id})


@router.post("/projects/{project_id}/approve")
def approve_project(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise BizError(ERR["NOT_FOUND"], "项目不存在")
    p.status = "active"
    db.commit()
    return ok({"id": p.id, "status": "active"})


@router.get("/projects/{project_id}/stakeholders")
def list_stakeholders(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(ProjectStakeholder).filter(
        ProjectStakeholder.project_id == project_id,
        ProjectStakeholder.deleted_at.is_(None),
    ).all()
    result = []
    for r in rows:
        u = db.query(User).filter(User.id == r.user_id).first()
        result.append({
            "id": r.id, "user_id": r.user_id, "user_name": u.name if u else None,
            "role_label": r.role_label,
        })
    return ok(result)


@router.get("/programs")
def list_programs(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Program).filter(Program.deleted_at.is_(None)).all()
    return ok([{
        "id": p.id, "code": p.code, "name": p.name,
        "owner_user_id": p.owner_user_id, "status": p.status,
    } for p in rows])
