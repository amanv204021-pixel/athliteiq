"""
Scout-facing endpoints -- browse athletes and review flagged submissions.

This closes a gap in the original: the User model had a `role` column with
"scout" and "admin" values, and get_assessment checked for them, but there
were no scout endpoints at all, so the role was unreachable in practice.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..ai.config import EXERCISE_CONFIG, SUPPORTED_TESTS
from ..database import get_db

router = APIRouter(prefix="/scouts", tags=["Scouts"])


@router.get("/athletes", response_model=list[schemas.UserOut])
def list_athletes(
    state: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Match on athlete name"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_scout),
):
    q = db.query(models.User).filter(models.User.role == "athlete")
    if state:
        q = q.filter(func.lower(models.User.state) == state.lower())
    if search:
        q = q.filter(models.User.name.ilike(f"%{search}%"))
    return q.order_by(models.User.name).limit(limit).all()


@router.get("/athletes/{user_id}/assessments", response_model=list[schemas.AssessmentOut])
def athlete_assessments(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_scout),
):
    athlete = db.query(models.User).filter(models.User.id == user_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return (
        db.query(models.Assessment)
        .filter(models.Assessment.user_id == user_id)
        .order_by(models.Assessment.submitted_at.desc())
        .all()
    )


@router.get("/flagged", response_model=list[schemas.AssessmentWithAthlete])
def flagged_assessments(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_scout),
):
    """Submissions the integrity heuristics flagged, for manual review."""
    rows = (
        db.query(models.Assessment, models.User)
        .join(models.User, models.Assessment.user_id == models.User.id)
        .filter(models.Assessment.status == "flagged")
        .order_by(models.Assessment.submitted_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for a, u in rows:
        item = schemas.AssessmentWithAthlete.model_validate(a)
        item.athlete_name = u.name
        item.athlete_state = u.state
        out.append(item)
    return out


@router.post("/assessments/{assessment_id}/review", response_model=schemas.AssessmentOut)
def review_assessment(
    assessment_id: int,
    approve: bool = Query(..., description="True = clear the flag, False = reject"),
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_scout),
):
    """Resolve a flagged submission: approve it onto the leaderboard, or reject it."""
    a = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    a.status = "completed" if approve else "rejected"
    db.commit()
    db.refresh(a)
    return a


# ------------------------------------------------------------------ meta ---
meta_router = APIRouter(tags=["Meta"])


@meta_router.get("/test-types", response_model=list[schemas.TestTypeInfo])
def list_test_types():
    """
    Every supported test, straight from EXERCISE_CONFIG. The frontend renders
    its dropdowns from this, so adding a sport to the config makes it appear
    in the UI with no frontend change.
    """
    return [
        schemas.TestTypeInfo(
            key=key,
            display_name=cfg["display_name"],
            type=cfg["type"],
            unit=cfg.get("unit", "reps"),
            higher_is_better=cfg.get("higher_is_better", True),
        )
        for key, cfg in sorted(EXERCISE_CONFIG.items())
    ]


@meta_router.get("/stats", response_model=schemas.StatsOut)
def platform_stats(db: Session = Depends(get_db)):
    """Headline numbers for the landing page."""
    return schemas.StatsOut(
        total_athletes=db.query(models.User).filter(models.User.role == "athlete").count(),
        total_assessments=db.query(models.Assessment).count(),
        completed_assessments=db.query(models.Assessment)
        .filter(models.Assessment.status == "completed")
        .filter(models.Assessment.ai_result["source"].as_string() != "demo_seed")
        .count(),
        states_represented=db.query(models.User.state)
        .filter(models.User.state.isnot(None), models.User.state != "")
        .distinct()
        .count(),
    )
