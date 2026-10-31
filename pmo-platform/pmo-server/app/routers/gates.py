"""门禁与评审路由（M4）。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import BizError, ERR, ok
from app.models.project import Gate, Review, ReviewItem, ReviewSignoff, ChecklistInstance
from app.models.identity import User

router = APIRouter()


class DecisionReq(BaseModel):
    decision: str  # pass/conditional/fail/waive
    waive_reason: Optional[str] = None


@router.get("/projects/{project_id}/gates")
def list_gates(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Gate).filter(
        Gate.project_id == project_id, Gate.deleted_at.is_(None)
    ).order_by(Gate.id).all()
    return ok([{
        "id": g.id, "name": g.name, "status": g.status, "decision": g.decision,
        "is_high_risk": g.is_high_risk, "enforce_mode": g.enforce_mode,
        "blocked_flag": g.blocked_flag, "stage_id": g.stage_id,
    } for g in rows])


@router.get("/gates/{gate_id}")
def get_gate(gate_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    g = db.query(Gate).filter(Gate.id == gate_id).first()
    if not g:
        raise BizError(ERR["NOT_FOUND"], "门禁不存在")
    data = {
        "id": g.id, "name": g.name, "status": g.status, "decision": g.decision,
        "is_high_risk": g.is_high_risk, "blocked_flag": g.blocked_flag,
        "gap_items": g.gap_items or [], "waive_reason": g.waive_reason,
    }
    # Checklist
    ci = db.query(ChecklistInstance).filter(ChecklistInstance.gate_id == gate_id).first()
    data["checklist"] = {
        "items": ci.items if ci else [],
        "total_count": ci.total_count if ci else 0,
        "done_count": ci.done_count if ci else 0,
    }
    # 评审
    reviews = db.query(Review).filter(Review.gate_id == gate_id, Review.deleted_at.is_(None)).all()
    data["reviews"] = [{
        "id": r.id, "title": r.title, "status": r.status,
        "scheduled_at": str(r.scheduled_at) if r.scheduled_at else None,
        "conclusion": r.conclusion,
    } for r in reviews]
    return ok(data)


@router.post("/gates/{gate_id}/decision")
def gate_decision(gate_id: int, req: DecisionReq, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = db.query(Gate).filter(Gate.id == gate_id).first()
    if not g:
        raise BizError(ERR["NOT_FOUND"], "门禁不存在")
    g.decision = req.decision
    g.decided_by = user.id
    g.decided_at = datetime.now()
    if req.decision == "pass":
        g.status = "passed"
        g.blocked_flag = False
    elif req.decision == "conditional":
        g.status = "conditional"
        g.blocked_flag = True
    elif req.decision == "fail":
        g.status = "failed"
        g.blocked_flag = True
    elif req.decision == "waive":
        if not req.waive_reason:
            raise BizError(ERR["BAD_REQUEST"], "豁免必须填写风险接受说明")
        g.status = "waived"
        g.waive_reason = req.waive_reason
        g.blocked_flag = False
    db.commit()
    return ok({"id": g.id, "status": g.status})


@router.post("/gates/{gate_id}/submit-review")
def submit_review(gate_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    g = db.query(Gate).filter(Gate.id == gate_id).first()
    if not g:
        raise BizError(ERR["NOT_FOUND"], "门禁不存在")
    g.status = "in_review"
    db.commit()
    return ok({"id": g.id, "status": "in_review"})


# ---------------- Review Items ----------------
class ReviewItemCreate(BaseModel):
    review_id: int
    kind: str
    content: str
    owner_user_id: int
    due_date: Optional[str] = None


@router.post("/reviews/items")
def create_review_item(req: ReviewItemCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from datetime import date
    ri = ReviewItem(
        review_id=req.review_id, kind=req.kind, content=req.content,
        owner_user_id=req.owner_user_id,
        due_date=date.fromisoformat(req.due_date) if req.due_date else None,
    )
    db.add(ri)
    db.commit()
    return ok({"id": ri.id})


@router.get("/reviews/{review_id}/items")
def list_review_items(review_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(ReviewItem).filter(
        ReviewItem.review_id == review_id, ReviewItem.deleted_at.is_(None)
    ).all()
    return ok([{
        "id": r.id, "kind": r.kind, "content": r.content,
        "owner_user_id": r.owner_user_id, "due_date": str(r.due_date) if r.due_date else None,
        "status": r.status,
    } for r in rows])


@router.patch("/review-items/{item_id}")
def close_review_item(item_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    ri = db.query(ReviewItem).filter(ReviewItem.id == item_id).first()
    if ri:
        ri.status = "closed"
        ri.closed_at = datetime.now()
        db.commit()
    return ok({"id": item_id})
