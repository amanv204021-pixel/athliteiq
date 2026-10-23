"""
Tests for the AI analysis layer -- rep counting, scoring, integrity checks.
"""
import pytest

from app.ai.config import EXERCISE_CONFIG, SUPPORTED_TESTS, get_exercise, is_higher_better
from app.ai.exercise_detector import ExerciseAnalyzer


def feed_reps(analyzer, depth, count, frames_per_rep=7, start=0):
    """Drive the analyzer through `count` rep cycles reaching `depth` degrees."""
    i = start
    for _ in range(count):
        for ang in [170, 150, 120, depth, 120, 150, 170]:
            analyzer.add_frame(ang, i / 15, i, hip_y=0.5)
            i += 1
    return i


# ----------------------------------------------------------------- config --
def test_every_config_entry_is_wellformed():
    for key, cfg in EXERCISE_CONFIG.items():
        assert "display_name" in cfg
        assert cfg["type"] in ("rep_based", "hold_based", "jump_based")
        assert len(cfg["landmarks"]) == 3
        if cfg["type"] == "rep_based":
            assert cfg["down_angle"] < cfg["up_angle"], key


def test_unknown_exercise_raises():
    with pytest.raises(KeyError):
        get_exercise("quidditch")


def test_every_exercise_is_constructible():
    """Regression: config listed 11 exercises but only 2 had any code."""
    for key in SUPPORTED_TESTS:
        ExerciseAnalyzer(key)


# ------------------------------------------------------------ rep counting --
def test_counts_clean_reps():
    a = ExerciseAnalyzer("squat")
    feed_reps(a, depth=85, count=6)
    assert a.rep_count == 6


def test_partial_reps_do_not_count():
    """A rep that never passes the 'down' threshold isn't a rep."""
    a = ExerciseAnalyzer("squat")
    feed_reps(a, depth=115, count=5)   # down_angle is 100
    assert a.rep_count == 0


def test_bad_form_counted_once_per_rep_not_per_frame():
    """Regression: the original incremented bad_form_count on every frame in
    the 100-140 band, so one slow descent racked up hundreds of penalties."""
    a = ExerciseAnalyzer("squat")
    # long, slow descent through the mid-range then a full rep
    i = 0
    for ang in [170] * 5 + [150] * 20 + [120] * 20 + [85] + [120] * 10 + [170]:
        a.add_frame(ang, i / 15, i, hip_y=0.5)
        i += 1
    assert a.rep_count == 1
    assert a.bad_form_reps <= 1


def test_no_pose_frames_are_tracked_separately():
    a = ExerciseAnalyzer("squat")
    for i in range(30):
        a.add_frame(None, i / 15, i)
    assert a.frames_analysed == 30
    assert a.frames_with_pose == 0


# ----------------------------------------------------------------- holds ---
def test_hold_accumulates_only_in_range():
    a = ExerciseAnalyzer("plank")
    for i in range(150):
        a.add_frame(172, i / 15, i)        # in range (min 160)
    good = a.hold_seconds
    for i in range(150, 300):
        a.add_frame(120, i / 15, i)        # out of range
    assert a.hold_seconds == pytest.approx(good)
    assert good > 9


def test_wall_sit_respects_upper_bound():
    a = ExerciseAnalyzer("wall_sit")       # 80..100
    for i in range(60):
        a.add_frame(140, i / 15, i)        # too straight
    assert a.hold_seconds == 0


# ---------------------------------------------------------------- scoring --
def test_scores_never_exceed_100():
    """Regression: accuracy could exceed 100 (base 70 + bonus, unclamped)."""
    a = ExerciseAnalyzer("squat")
    feed_reps(a, depth=85, count=60)
    s = a.calculate_score(duration_sec=30)
    for k, v in s.items():
        assert 0 <= v <= 100, f"{k}={v}"


def test_scores_never_negative():
    a = ExerciseAnalyzer("squat")
    feed_reps(a, depth=115, count=20)      # all partial
    s = a.calculate_score(duration_sec=200)
    for k, v in s.items():
        assert v >= 0, f"{k}={v}"


def test_zero_duration_does_not_divide_by_zero():
    a = ExerciseAnalyzer("squat")
    s = a.calculate_score(duration_sec=0)
    assert s["overall_score"] >= 0


def test_clean_beats_sloppy():
    clean = ExerciseAnalyzer("squat"); feed_reps(clean, 85, 10)
    sloppy = ExerciseAnalyzer("squat")
    i = 0
    for _ in range(10):
        i = feed_reps(sloppy, 85, 1, start=i)
        i = feed_reps(sloppy, 112, 1, start=i)   # partial between each
    assert clean.finalize(20).scores["overall_score"] >= sloppy.finalize(20).scores["overall_score"]


# ------------------------------------------------------------- integrity ---
def test_flags_when_no_person_detected():
    a = ExerciseAnalyzer("squat")
    for i in range(60):
        a.add_frame(None, i / 15, i)
    result = a.finalize(4.0)
    assert "no_person_detected" in result.cheat_flags
    assert result.to_dict()["cheat_detected"] is True


def test_flags_implausible_rep_rate():
    a = ExerciseAnalyzer("squat")
    feed_reps(a, 85, 30)
    flags = a.detect_cheating(coverage=0.95, duration_sec=5)
    assert "implausible_rep_rate" in flags


def test_clean_run_has_no_flags():
    a = ExerciseAnalyzer("squat")
    feed_reps(a, 85, 12)
    assert a.detect_cheating(coverage=0.95, duration_sec=30) == []


# -------------------------------------------------------------- finalize ---
def test_finalize_payload_is_complete():
    a = ExerciseAnalyzer("pushup")
    feed_reps(a, 80, 12)
    d = a.finalize(25).to_dict()
    for key in ("test_type", "reps", "scores", "suggestions", "cheat_detected", "unit", "score"):
        assert key in d
    assert d["source"] == "uploaded_video"
    assert d["score"] == 12
    assert d["unit"] == "reps"


def test_hold_primary_score_is_seconds():
    a = ExerciseAnalyzer("plank")
    for i in range(300):
        a.add_frame(175, i / 15, i)
    d = a.finalize(20).to_dict()
    assert d["unit"] == "seconds"
    assert d["score"] > 15


def test_suggestions_always_present():
    for key in SUPPORTED_TESTS:
        a = ExerciseAnalyzer(key)
        feed_reps(a, 85, 3)
        assert len(a.finalize(10).suggestions) >= 1


# ----------------------------------------------------------- leaderboard ---
def test_ranking_direction_from_config():
    assert is_higher_better("squat") is True
    assert is_higher_better("unknown_test") is True
