from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.evaluation import Evaluation
from app.models.user import Role, User
from app.schemas.evaluation import EvaluationCreate, EvaluationOut, EmployeeEvalStats, EvaluationStatsPoint

router = APIRouter(prefix="/evaluations", tags=["评价"])


def _today() -> str:
    return date.today().isoformat()


def _build_out_map(ev_list: list[Evaluation], db: Session) -> dict[int, EvaluationOut]:
    """Batch-load all referenced users, then build EvaluationOut objects."""
    user_ids = set()
    for ev in ev_list:
        user_ids.add(ev.evaluator_id)
        user_ids.add(ev.subject_id)
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    result = {}
    for ev in ev_list:
        evaluator = users.get(ev.evaluator_id)
        subject = users.get(ev.subject_id)
        result[ev.id] = EvaluationOut(
            id=ev.id,
            evaluator_id=ev.evaluator_id,
            evaluator_name=evaluator.full_name if evaluator else "",
            subject_id=ev.subject_id,
            subject_name=subject.full_name if subject else "",
            target_type=ev.target_type,
            target_id=ev.target_id,
            score=ev.score,
            comment=ev.comment,
            created_at=str(ev.created_at)[:10],
        )
    return result


@router.post("", response_model=EvaluationOut)
def create_evaluation(
    body: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("boss", "super_admin")),
):
    subject = db.get(User, body.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="被评价员工不存在")
    if subject.role.name in ("boss", "super_admin"):
        raise HTTPException(status_code=400, detail="不支持对老板或超管进行评价")
    ev = Evaluation(
        evaluator_id=current_user.id,
        subject_id=body.subject_id,
        target_type=body.target_type,
        target_id=body.target_id,
        score=body.score,
        comment=body.comment,
        created_at=_today(),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    out_map = _build_out_map([ev], db)
    return out_map[ev.id]


@router.get("/stats", response_model=list[EmployeeEvalStats])
def evaluation_stats(
    period: str = Query("month", pattern="^(week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    返回折线图数据，按日聚合日均分。
    period=week  → 最近7天
    period=month → 最近30天
    老板/超管返回所有员工多折线，员工返回自己单折线。
    """
    days = 7 if period == "week" else 30
    start = (date.today() - timedelta(days=days - 1)).isoformat()

    is_manager = current_user.role.name in ("boss", "super_admin")

    employee_role_ids = [
        r.id for r in db.query(Role).filter(Role.name == "salesperson").all()
    ]

    q = (
        db.query(
            Evaluation.subject_id,
            Evaluation.created_at,
            func.avg(Evaluation.score).label("avg_score"),
            func.count(Evaluation.id).label("cnt"),
        )
        .join(User, User.id == Evaluation.subject_id)
        .filter(Evaluation.created_at >= start)
        .filter(User.role_id.in_(employee_role_ids))
        .group_by(Evaluation.subject_id, Evaluation.created_at)
    )
    if not is_manager:
        q = q.filter(Evaluation.subject_id == current_user.id)

    rows = q.all()

    subject_ids = list({r.subject_id for r in rows})
    users_map = {}
    if subject_ids:
        users_map = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(subject_ids)).all()}

    by_subject: dict[int, list] = {}
    for r in rows:
        by_subject.setdefault(r.subject_id, []).append(
            EvaluationStatsPoint(
                date=str(r.created_at)[:10],
                avg_score=round(float(r.avg_score), 2),
                count=r.cnt,
            )
        )

    result = []
    for sid, points in by_subject.items():
        points_sorted = sorted(points, key=lambda p: p.date)
        result.append(EmployeeEvalStats(
            subject_id=sid,
            subject_name=users_map.get(sid, f"员工#{sid}"),
            points=points_sorted,
        ))
    return result


@router.get("", response_model=list[EvaluationOut])
def list_evaluations(
    target_type: Optional[str] = Query(None),
    target_id: Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """老板/超管可查所有；员工只能查自己 subject_id 的评价。"""
    is_manager = current_user.role.name in ("boss", "super_admin")
    q = db.query(Evaluation)
    if target_type:
        q = q.filter(Evaluation.target_type == target_type)
    if target_id is not None:
        q = q.filter(Evaluation.target_id == target_id)
    if subject_id is not None:
        q = q.filter(Evaluation.subject_id == subject_id)
    if not is_manager:
        q = q.filter(Evaluation.subject_id == current_user.id)
    evs = q.order_by(Evaluation.created_at.desc()).all()
    out_map = _build_out_map(evs, db)
    return [out_map[e.id] for e in evs]


@router.delete("/{ev_id}")
def delete_evaluation(
    ev_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("boss", "super_admin")),
):
    ev = db.get(Evaluation, ev_id)
    if not ev:
        raise HTTPException(status_code=404, detail="评价不存在")
    db.delete(ev)
    db.commit()
    return {"ok": True}
