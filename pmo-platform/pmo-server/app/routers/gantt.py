"""甘特图路由（frappe-gantt 数据格式）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import ok
from app.models.task import Task, Dependency, Baseline, BaselineTask
from app.models.identity import User

router = APIRouter()


@router.get("/projects/{project_id}/gantt")
def get_gantt(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    tasks = db.query(Task).filter(
        Task.project_id == project_id, Task.deleted_at.is_(None)
    ).all()

    # 依赖映射：successor -> 逗号分隔的 predecessor ids
    preds_map = {}
    deps = db.query(Dependency).filter(Dependency.deleted_at.is_(None)).all()
    task_ids = {t.id for t in tasks}
    for d in deps:
        if d.successor_task_id in task_ids and d.predecessor_task_id in task_ids:
            preds_map.setdefault(d.successor_task_id, []).append(f"t{d.predecessor_task_id}")

    # 基线
    baseline = db.query(Baseline).filter(
        Baseline.project_id == project_id, Baseline.deleted_at.is_(None)
    ).order_by(Baseline.snapshot_at.desc()).first()
    baseline_map = {}
    if baseline:
        bts = db.query(BaselineTask).filter(BaselineTask.baseline_id == baseline.id).all()
        for bt in bts:
            baseline_map[bt.task_id] = bt

    gantt_tasks = []
    critical_path = []
    for t in tasks:
        owner = db.query(User).filter(User.id == t.owner_user_id).first()
        bt = baseline_map.get(t.id)
        item = {
            "id": f"t{t.id}",
            "name": t.name,
            "start": str(t.plan_start),
            "end": str(t.plan_end),
            "progress": float(t.progress_pct or 0),
            "dependencies": ",".join(preds_map.get(t.id, [])),
            "custom_class": "is-critical" if t.is_critical else "",
            "owner": {"id": t.owner_user_id, "name": owner.name if owner else ""},
            "is_milestone": t.is_milestone,
            "status": t.status,
        }
        if bt:
            item["baseline"] = {
                "start": str(bt.plan_start), "end": str(bt.plan_end),
            }
        gantt_tasks.append(item)
        if t.is_critical:
            critical_path.append(f"t{t.id}")

    return ok({
        "tasks": gantt_tasks,
        "critical_path": critical_path,
        "baseline_name": baseline.name if baseline else None,
    })
