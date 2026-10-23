from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    state = Column(String, index=True)
    district = Column(String)
    role = Column(String, default="athlete", nullable=False)  # athlete | scout | admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assessments = relationship(
        "Assessment", back_populates="user", cascade="all, delete-orphan"
    )


class Assessment(Base):
    """
    One row per test attempt (e.g. vertical jump, squat, plank).
    video_url points to the uploaded clip; ai_result stores the full model
    output (rep count, sub-scores, cheat flags, coaching suggestions).
    """
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    test_type = Column(String, nullable=False, index=True)
    video_url = Column(String, nullable=False)
    # processing | completed | failed | flagged
    status = Column(String, default="processing", nullable=False, index=True)
    score = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    ai_result = Column(JSON, nullable=True)
    # NEW: surfaces why an analysis failed instead of leaving rows stuck
    # on "processing" forever, which the original had no way to express.
    error_message = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="assessments")
