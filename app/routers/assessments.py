"""
Assessment upload + retrieval.

Key changes vs the original:
  * run_ai_analysis no longer returns hardcoded mock numbers -- it runs the
    real MediaPipe pose pipeline over the uploaded video.
  * Upload validates extension and enforces a size cap while streaming, so a
    huge or non-video file can't fill the disk or crash the analyzer.
  * The filename is generated, never derived from user input (the original
    did `file.filename.split(".")[-1]`, which crashes on extensionless names
    and lets the client influence the stored path).
  * Failures mark the row `failed` with a message instead of leaving it
    stuck on "processing" forever.
"""
from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..ai.config import EXERCISE_CONFIG, SUPPORTED_TESTS
from ..config import settings
from ..database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assessments", tags=["Assessments"])


def run_ai_analysis(assessment_id: int, test_type: str, video_path: str) -> None:
    """
    Real AI pipeline: pose estimation -> rep counting -> scoring.

    Runs as a FastAPI BackgroundTask and opens its own DB session, since it
    executes outside the request's session lifecycle.

    For production scale this should move to a Celery/RQ worker or a
    dedicated GPU inference service -- video analysis is CPU-heavy and
    shouldn't share the web process. The call boundary here is the seam.
    """
    # Imported lazily so the API still boots if OpenCV/MediaPipe are absent.
    from ..ai.video_analyzer import analyze_video
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        assessment = (
            db.query(models.Assessment)
            .filter(models.Assessment.id == assessment_id)
            .first()
        )
        if not assessment:
            logger.warning("assessment %s vanished before analysis", assessment_id)
            return

        try:
            result = analyze_video(video_path, test_type, max_frames=settings.MAX_FRAMES)
            payload = result.to_dict()

            assessment.score = payload["score"]
            assessment.unit = payload["unit"]
            assessment.ai_result = payload
            # Flag suspicious submissions for scout review rather than
            # silently publishing them to the leaderboard.
            assessment.status = "flagged" if payload["cheat_detected"] else "completed"
            assessment.error_message = None
        except Exception as exc:
            logger.exception("AI analysis failed for assessment %s", assessment_id)
            assessment.status = "failed"
            assessment.error_message = f"{type(exc).__name__}: {exc}"[:500]

        assessment.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _save_upload(file: UploadFile) -> Path:
    """
    Stream the upload to disk with a size cap.

    Reading the whole file into memory (or copying it unchecked) would let a
    single large upload exhaust RAM/disk -- the original had no limit.
    """
    original = Path(file.filename or "")
    ext = original.suffix.lower()
    if ext not in settings.ALLOWED_VIDEO_EXT:
        allowed = ", ".join(sorted(settings.ALLOWED_VIDEO_EXT))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext or 'unknown'}'. Allowed: {allowed}",
        )

    dest = settings.UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    limit = settings.max_upload_bytes
    written = 0

    try:
        with dest.open("wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                written += len(chunk)
                if written > limit:
                    buffer.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Could not save upload: {exc}")
    finally:
        file.file.close()

    if written == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    return dest


@router.post("/upload", response_model=schemas.AssessmentOut, status_code=201)
def upload_assessment(
    background_tasks: BackgroundTasks,
    test_type: str = Form(..., description=f"One of: {', '.join(SUPPORTED_TESTS)}"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # BUGFIX: the original accepted ANY test_type string, then silently
    # scored it 0 via the mock dict's .get() fallback.
    if test_type not in SUPPORTED_TESTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown test_type '{test_type}'. Supported: {', '.join(SUPPORTED_TESTS)}",
        )

    filepath = _save_upload(file)

    assessment = models.Assessment(
        user_id=current_user.id,
        test_type=test_type,
        video_url=str(filepath),
        status="processing",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Return immediately; analysis continues in the background.
    background_tasks.add_task(run_ai_analysis, assessment.id, test_type, str(filepath))
    return assessment


@router.get("/me", response_model=list[schemas.AssessmentOut])
def my_assessments(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return (
        db.query(models.Assessment)
        .filter(models.Assessment.user_id == current_user.id)
        .order_by(models.Assessment.submitted_at.desc(), models.Assessment.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/{assessment_id}", response_model=schemas.AssessmentOut)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    assessment = (
        db.query(models.Assessment)
        .filter(models.Assessment.id == assessment_id)
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.user_id != current_user.id and current_user.role not in ("scout", "admin"):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this assessment"
        )
    return assessment


@router.delete("/{assessment_id}", status_code=204)
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Athletes can withdraw their own submissions (also removes the video)."""
    assessment = (
        db.query(models.Assessment)
        .filter(models.Assessment.id == assessment_id)
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    if assessment.video_url:
        Path(assessment.video_url).unlink(missing_ok=True)
    db.delete(assessment)
    db.commit()
    return None


@router.post("/live", response_model=schemas.AssessmentOut, status_code=201)
def submit_live_result(
    payload: schemas.LiveResultIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Record the result of an on-device live camera assessment.

    Live mode runs MediaPipe in the browser so the athlete's video never
    leaves their phone. That means there is no footage for the server to
    re-analyse, so this payload is untrusted by definition. We therefore:

      * validate test_type against the config
      * re-derive the headline score from the raw counts instead of taking
        the client's `score` field
      * re-run the integrity heuristics server-side
      * tag the source as a live camera session or a locally analysed clip

    An uploaded video remains the higher-trust path; live results are
    convenient but self-reported.
    """
    if payload.test_type not in SUPPORTED_TESTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown test_type '{payload.test_type}'. Supported: {', '.join(SUPPORTED_TESTS)}",
        )

    cfg = EXERCISE_CONFIG[payload.test_type]
    kind = cfg["type"]

    # Re-derive the headline number from the raw counts. A client that
    # inflates `score` directly gets ignored.
    if kind == "hold_based":
        score = round(payload.hold_seconds, 2)
    elif kind == "jump_based":
        score = round(payload.jump_height_cm or 0.0, 2)
    else:
        score = float(payload.reps)

    # Server-side integrity checks, mirroring ExerciseAnalyzer.detect_cheating.
    flags: list[str] = []
    if payload.pose_coverage < 0.5:
        flags.append("body_not_consistently_visible")
    if payload.duration_sec < 2.0:
        flags.append("video_too_short")
    if payload.reps and payload.duration_sec > 0:
        if payload.reps / payload.duration_sec > 3.0:
            flags.append("implausible_rep_rate")
    if payload.frames_with_pose == 0:
        flags.append("no_person_detected")
    if payload.bad_form_reps > payload.reps:
        flags.append("inconsistent_rep_counts")
    if payload.frames_with_pose > payload.frames_analysed:
        flags.append("inconsistent_frame_counts")

    result = payload.model_dump()
    result.update({
        "display_name": cfg["display_name"],
        "score": score,
        "unit": cfg.get("unit", payload.unit),
        "cheat_detected": bool(flags),
        "cheat_flags": flags,
        "source": payload.source,
    })

    assessment = models.Assessment(
        user_id=current_user.id,
        test_type=payload.test_type,
        video_url="",  # nothing stored: the video stayed on the device
        status="flagged" if flags else "completed",
        score=score,
        unit=cfg.get("unit", payload.unit),
        ai_result=result,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment
