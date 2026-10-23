"""
Leaderboard -- the core "democratizing access" feature: scouts filter top
performers regionally, so talent in remote areas becomes visible without
attending an in-person trial.

BUGFIXES vs the original:
  1. Sorted score DESC for every test. For time-based tests (shuttle run)
     lower is better, so the slowest athletes were ranked first. Direction
     now comes from the exercise config.
  2. Returned one row per ATTEMPT, so a single athlete with 10 uploads filled
     the entire top 10. Now returns each athlete's personal best.
  3. Included rows where score IS NULL, which crashed serialization because
     LeaderboardEntry.score is non-optional. Now filtered out.
  4. No rank field -- the client had to infer position.
  5. "flagged" (suspected cheating) rows were eligible for the leaderboard.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..ai.config import EXERCISE_CONFIG, SUPPORTED_TESTS, is_higher_better
from ..database import get_db

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("", response_model=list[schemas.LeaderboardEntry])
def get_leaderboard(
    test_type: str = Query(..., description=f"One of: {', '.join(SUPPORTED_TESTS)}"),
    state: Optional[str] = Query(None, description="Filter by state for regional scouting"),
    district: Optional[str] = Query(None, description="Filter by district"),
    gender: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None, ge=5, le=100),
    max_age: Optional[int] = Query(None, ge=5, le=100),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if test_type not in EXERCISE_CONFIG:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown test_type '{test_type}'. Supported: {', '.join(SUPPORTED_TESTS)}",
        )

    higher_better = is_higher_better(test_type)
    unit = EXERCISE_CONFIG[test_type].get("unit")

    q = (
        db.query(models.Assessment, models.User)
        .join(models.User, models.Assessment.user_id == models.User.id)
        .filter(models.Assessment.test_type == test_type)
        .filter(models.Assessment.status == "completed")
        .filter(models.Assessment.score.isnot(None))
    )

    if state:
        q = q.filter(func.lower(models.User.state) == state.lower())
    if district:
        q = q.filter(func.lower(models.User.district) == district.lower())
    if gender:
        q = q.filter(func.lower(models.User.gender) == gender.lower())
    if min_age is not None:
        q = q.filter(models.User.age >= min_age)
    if max_age is not None:
        q = q.filter(models.User.age <= max_age)

    order = (
        models.Assessment.score.desc() if higher_better else models.Assessment.score.asc()
    )
    # Pull a generous window, then reduce to one personal best per athlete.
    rows = q.order_by(order).limit(limit * 10).all()

    best: dict[int, tuple] = {}
    for assessment, user in rows:
        current = best.get(user.id)
        if current is None:
            best[user.id] = (assessment, user)
        else:
            prev = current[0].score
            if (higher_better and assessment.score > prev) or (
                not higher_better and assessment.score < prev
            ):
                best[user.id] = (assessment, user)

    ranked = sorted(
        best.values(), key=lambda pair: pair[0].score, reverse=higher_better
    )[:limit]

    return [
        schemas.LeaderboardEntry(
            rank=i,
            user_id=user.id,
            name=user.name,
            state=user.state,
            district=user.district,
            age=user.age,
            test_type=assessment.test_type,
            source=(assessment.ai_result or {}).get("source"),
            score=assessment.score,
            unit=assessment.unit or unit,
            assessment_id=assessment.id,
            submitted_at=assessment.submitted_at,
        )
        for i, (assessment, user) in enumerate(ranked, start=1)
    ]


@router.get("/states", response_model=list[str])
def list_states(db: Session = Depends(get_db)):
    """States that actually have athletes -- powers the filter dropdown."""
    rows = (
        db.query(models.User.state)
        .filter(models.User.state.isnot(None), models.User.state != "")
        .distinct()
        .order_by(models.User.state)
        .all()
    )
    return [r[0] for r in rows]
