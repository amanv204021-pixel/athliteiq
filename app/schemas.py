from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------- users ----
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    # BUGFIX: password had no constraints at all -- empty strings were
    # accepted. Max length matches bcrypt's practical input limit.
    password: str = Field(..., min_length=6, max_length=128)
    age: Optional[int] = Field(None, ge=5, le=100)
    gender: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    role: Literal["athlete", "scout"] = "athlete"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    age: Optional[int] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    role: str
    created_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserOut] = None


# ---------------------------------------------------------- assessments ----
class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_type: str
    status: str
    score: Optional[float] = None
    unit: Optional[str] = None
    ai_result: Optional[Any] = None
    error_message: Optional[str] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LiveScores(BaseModel):
    posture: int = Field(..., ge=0, le=100)
    balance: int = Field(..., ge=0, le=100)
    accuracy: int = Field(..., ge=0, le=100)
    speed: int = Field(..., ge=0, le=100)
    overall_score: int = Field(..., ge=0, le=100)


class LiveResultIn(BaseModel):
    """
    Result computed on the athlete's device during a live camera session.

    The video never leaves the phone, so the server cannot recompute this
    from source footage. Everything here is therefore treated as untrusted
    input: bounds are enforced by the schema, and the route re-derives the
    headline score and the integrity flags rather than believing the client.
    """
    test_type: str
    source: Literal["live_camera", "local_video"] = "live_camera"
    reps: int = Field(0, ge=0, le=10_000)
    hold_seconds: float = Field(0.0, ge=0, le=86_400)
    jump_height_cm: Optional[float] = Field(None, ge=0, le=300)
    duration_sec: float = Field(0.0, ge=0, le=86_400)
    bad_form_reps: int = Field(0, ge=0, le=10_000)
    frames_analysed: int = Field(0, ge=0)
    frames_with_pose: int = Field(0, ge=0)
    pose_coverage: float = Field(0.0, ge=0, le=1)
    scores: LiveScores
    suggestions: list[str] = []
    unit: str = "reps"


class AssessmentWithAthlete(AssessmentOut):
    """Assessment plus athlete info -- used by scout-facing endpoints."""
    athlete_name: Optional[str] = None
    athlete_state: Optional[str] = None


# ---------------------------------------------------------- leaderboard ----
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    name: str
    state: Optional[str] = None
    district: Optional[str] = None
    age: Optional[int] = None
    test_type: str
    source: Optional[str] = None
    score: float
    unit: Optional[str] = None
    assessment_id: int
    submitted_at: Optional[datetime] = None


# --------------------------------------------------------------- tests -----
class TestTypeInfo(BaseModel):
    """Describes one supported test so the frontend can render it dynamically."""
    key: str
    display_name: str
    type: str
    unit: str
    higher_is_better: bool


class StatsOut(BaseModel):
    total_athletes: int
    total_assessments: int
    completed_assessments: int
    states_represented: int
