"""
exercise_detector.py
--------------------
Rep counting, hold timing, scoring and coaching feedback.

REWRITE NOTE: the original version hardcoded one method per exercise
(analyze_pushup, analyze_squat) even though config.py already described
every exercise declaratively -- so adding a sport meant editing code, and
9 of the 11 configured exercises had no implementation at all. Worse, this
module was imported by *nothing*: the API returned hardcoded mock scores.

It is now a single config-driven state machine that handles every entry in
EXERCISE_CONFIG, and it is wired into the upload pipeline for real.

Also fixed: the old analyze_squat incremented bad_form_count on every frame
in the 100-140 degree band. At 30fps a normal descent passes through that
band repeatedly, so a perfect athlete accumulated hundreds of "bad form"
penalties. Form is now judged once per completed rep.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .config import get_exercise


@dataclass
class RepEvent:
    """One completed repetition and how clean it was."""
    index: int
    peak_angle: float       # deepest angle reached during the rep
    bottomed_out: bool      # did it reach full depth/extension?
    frame: int


@dataclass
class AnalysisResult:
    test_type: str
    display_name: str
    source: str = "uploaded_video"
    reps: int = 0
    hold_seconds: float = 0.0
    jump_height_cm: Optional[float] = None
    duration_sec: float = 0.0
    bad_form_reps: int = 0
    frames_analysed: int = 0
    frames_with_pose: int = 0
    scores: dict = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    cheat_flags: list[str] = field(default_factory=list)
    primary_score: float = 0.0
    unit: str = "reps"

    def to_dict(self) -> dict:
        return {
            "test_type": self.test_type,
            "display_name": self.display_name,
            "source": self.source,
            "reps": self.reps,
            "hold_seconds": round(self.hold_seconds, 2),
            "jump_height_cm": self.jump_height_cm,
            "duration_sec": round(self.duration_sec, 2),
            "bad_form_reps": self.bad_form_reps,
            "frames_analysed": self.frames_analysed,
            "frames_with_pose": self.frames_with_pose,
            "pose_coverage": (
                round(self.frames_with_pose / self.frames_analysed, 3)
                if self.frames_analysed else 0.0
            ),
            "scores": self.scores,
            "suggestions": self.suggestions,
            "cheat_detected": bool(self.cheat_flags),
            "cheat_flags": self.cheat_flags,
            "unit": self.unit,
            "score": self.primary_score,
        }


class ExerciseAnalyzer:
    """
    Feeds on a stream of (angle, timestamp) samples and produces reps,
    hold time, scores and suggestions -- driven entirely by EXERCISE_CONFIG.
    """

    def __init__(self, test_type: str):
        self.test_type = test_type
        self.cfg = get_exercise(test_type)
        self.kind = self.cfg["type"]

        self.stage: Optional[str] = None
        self.reps: list[RepEvent] = []
        self.hold_seconds = 0.0
        self.frames_analysed = 0
        self.frames_with_pose = 0

        # per-rep tracking
        self._current_peak: Optional[float] = None
        self._last_ts: Optional[float] = None

        # jump tracking (hip y over time; image coords -> smaller y = higher)
        self._hip_y: list[float] = []

    # -- ingestion ----------------------------------------------------------
    def add_frame(
        self,
        angle: Optional[float],
        timestamp_sec: float,
        frame_index: int,
        hip_y: Optional[float] = None,
    ) -> None:
        """Feed one frame. `angle` is None when no body was detected."""
        self.frames_analysed += 1
        dt = 0.0 if self._last_ts is None else max(0.0, timestamp_sec - self._last_ts)
        self._last_ts = timestamp_sec

        if angle is None:
            return
        self.frames_with_pose += 1

        if hip_y is not None:
            self._hip_y.append(hip_y)

        if self.kind == "hold_based":
            self._track_hold(angle, dt)
        else:
            self._track_reps(angle, frame_index)

    def _track_hold(self, angle: float, dt: float) -> None:
        lo = self.cfg.get("hold_angle_min", 0)
        hi = self.cfg.get("hold_angle_max", 360)
        if lo <= angle <= hi:
            self.hold_seconds += dt
            self.stage = "holding"
        else:
            self.stage = "broken"

    def _track_reps(self, angle: float, frame_index: int) -> None:
        up = self.cfg["up_angle"]
        down = self.cfg["down_angle"]

        if angle > up:
            # Returned to the top. If we were down, the rep is complete.
            if self.stage == "down" and self._current_peak is not None:
                # Full depth means the athlete got meaningfully past the
                # 'down' threshold rather than just grazing it.
                bottomed = self._current_peak <= down
                self.reps.append(
                    RepEvent(
                        index=len(self.reps) + 1,
                        peak_angle=round(self._current_peak, 1),
                        bottomed_out=bottomed,
                        frame=frame_index,
                    )
                )
                self._current_peak = None
            self.stage = "up"

        elif angle < down:
            if self.stage == "up":
                self.stage = "down"
                self._current_peak = angle
            elif self.stage == "down":
                self._current_peak = min(self._current_peak or angle, angle)

        else:
            # Mid-range: track the extreme so partial reps can be judged.
            if self.stage == "down" and self._current_peak is not None:
                self._current_peak = min(self._current_peak, angle)

    # -- scoring ------------------------------------------------------------
    @property
    def rep_count(self) -> int:
        return len(self.reps)

    @property
    def bad_form_reps(self) -> int:
        """Reps that never reached full depth. Counted once per rep, not per frame."""
        return sum(1 for r in self.reps if not r.bottomed_out)

    def estimate_jump_height_cm(self) -> Optional[float]:
        """
        Rough vertical-jump estimate from hip displacement.

        Hip y is normalised (0-1) to frame height. We take the athlete's
        standing hip height as the baseline and the airborne minimum as the
        peak, then scale by an assumed frame height of ~2m of visible space.
        This is deliberately approximate -- a production system would
        calibrate against a known reference object in frame.
        """
        if len(self._hip_y) < 10:
            return None
        baseline = sorted(self._hip_y)[int(len(self._hip_y) * 0.75)]  # resting/low pose
        peak = min(self._hip_y)                                        # highest point
        delta_norm = max(0.0, baseline - peak)
        ASSUMED_FRAME_HEIGHT_CM = 200.0
        return round(delta_norm * ASSUMED_FRAME_HEIGHT_CM, 1)

    def calculate_score(self, duration_sec: float) -> dict:
        """
        Four sub-scores plus an overall. All clamped to 0-100.

        BUGFIX: the original could return an accuracy score above 100
        (base_score 70 + speed_bonus 10 with no upper clamp) and a
        posture score that ignored the exercise entirely.
        """
        reps = self.rep_count
        bad = self.bad_form_reps
        total = max(1, reps)

        clean_ratio = (reps - bad) / total if reps else 0.0
        coverage = (
            self.frames_with_pose / self.frames_analysed if self.frames_analysed else 0.0
        )

        if self.kind == "hold_based":
            # Score the hold against a 60s benchmark.
            volume = min(100.0, (self.hold_seconds / 60.0) * 100.0)
            posture = 100.0 * coverage
            balance = volume
            accuracy = volume
            speed = volume
        else:
            volume = min(100.0, reps * 5.0)
            posture = max(0.0, 100.0 * clean_ratio * (0.6 + 0.4 * coverage))
            balance = max(0.0, 100.0 * clean_ratio)
            accuracy = max(0.0, volume * (0.5 + 0.5 * clean_ratio))
            rate = reps / duration_sec if duration_sec > 0 else 0.0
            # ~0.5 reps/sec is a strong sustained pace.
            speed = min(100.0, (rate / 0.5) * 100.0)

        def clamp(v: float) -> int:
            return int(max(0, min(100, round(v))))

        scores = {
            "posture": clamp(posture),
            "balance": clamp(balance),
            "accuracy": clamp(accuracy),
            "speed": clamp(speed),
        }
        scores["overall_score"] = clamp(sum(scores.values()) / 4)
        return scores

    def detect_cheating(self, coverage: float, duration_sec: float) -> list[str]:
        """Heuristic integrity checks. Flags get surfaced to scouts."""
        flags: list[str] = []
        if coverage < 0.5:
            flags.append("body_not_consistently_visible")
        if duration_sec < 2.0:
            flags.append("video_too_short")
        if self.rep_count > 0 and duration_sec > 0:
            rate = self.rep_count / duration_sec
            if rate > 3.0:
                flags.append("implausible_rep_rate")
        if self.frames_with_pose == 0:
            flags.append("no_person_detected")
        return flags

    def generate_suggestions(self, scores: dict) -> list[str]:
        """Plain-language coaching feedback based on the sub-scores."""
        name = self.cfg["display_name"].lower()
        out: list[str] = []

        if self.kind == "hold_based":
            if self.hold_seconds < 20:
                out.append(f"Try to extend your {name} - aim for at least 30 seconds.")
            if scores["posture"] < 70:
                out.append("Keep your body in a straight line and your core braced.")
        else:
            if scores["accuracy"] < 60:
                out.append("Complete the full range of motion - partial reps don't count.")
            if scores["posture"] < 70:
                out.append(f"Watch your {name} form - keep your back straight and controlled.")
            if scores["balance"] < 70:
                out.append("Your movement looks unstable; tighten your core for stability.")
            if scores["speed"] < 50:
                out.append("Pick up the pace slightly while staying controlled.")
            if self.bad_form_reps > 3:
                out.append(
                    f"{self.bad_form_reps} reps didn't reach full depth - "
                    "quality matters more than quantity."
                )

        if self.frames_analysed and self.frames_with_pose / self.frames_analysed < 0.7:
            out.append("Reposition the camera so your whole body stays in frame.")

        if not out:
            out.append("Great performance! Keep this consistency up.")
        return out

    # -- final assembly -----------------------------------------------------
    def finalize(self, duration_sec: float) -> AnalysisResult:
        coverage = (
            self.frames_with_pose / self.frames_analysed if self.frames_analysed else 0.0
        )
        scores = self.calculate_score(duration_sec)
        flags = self.detect_cheating(coverage, duration_sec)

        result = AnalysisResult(
            test_type=self.test_type,
            display_name=self.cfg["display_name"],
            reps=self.rep_count,
            hold_seconds=self.hold_seconds,
            duration_sec=duration_sec,
            bad_form_reps=self.bad_form_reps,
            frames_analysed=self.frames_analysed,
            frames_with_pose=self.frames_with_pose,
            scores=scores,
            cheat_flags=flags,
            unit=self.cfg.get("unit", "reps"),
        )
        result.suggestions = self.generate_suggestions(scores)

        # Primary score = the headline number shown on the leaderboard.
        if self.kind == "hold_based":
            result.primary_score = round(self.hold_seconds, 2)
        elif self.kind == "jump_based":
            jump = self.estimate_jump_height_cm()
            result.jump_height_cm = jump
            result.primary_score = jump if jump is not None else 0.0
        else:
            result.primary_score = float(self.rep_count)

        return result
