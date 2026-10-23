"""
video_analyzer.py
-----------------
Ties the pieces together: read an uploaded video with OpenCV, run pose
detection per frame, feed angles into ExerciseAnalyzer, return real results.

This is the module that replaces the `run_ai_analysis` mock -- the original
just looked up a hardcoded dict of fake scores and never touched the video.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2

from .config import get_exercise
from .exercise_detector import AnalysisResult, ExerciseAnalyzer
from .pose_module import PoseDetector

logger = logging.getLogger(__name__)

# Cap how many frames we analyse so a long clip can't hang the worker.
DEFAULT_MAX_FRAMES = 900
# Analyse at most ~15 effective fps; most tests don't need more.
TARGET_FPS = 15.0


def analyze_video(
    video_path: str | Path,
    test_type: str,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> AnalysisResult:
    """
    Run the full pose -> rep-count -> score pipeline over one video file.

    Raises:
        FileNotFoundError: video missing
        KeyError:          unknown test_type
        RuntimeError:      video unreadable/corrupt
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    cfg = get_exercise(test_type)  # raises KeyError for unknown types
    a_name, b_name, c_name = cfg["landmarks"]

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        # Some phone/webm clips report 0 or absurd fps; fall back sanely.
        if not (1.0 <= fps <= 240.0):
            fps = 30.0

        # Skip frames to approximate TARGET_FPS.
        stride = max(1, int(round(fps / TARGET_FPS)))

        analyzer = ExerciseAnalyzer(test_type)
        detector = PoseDetector()

        frame_index = 0
        analysed = 0
        last_ts = 0.0

        try:
            while analysed < max_frames:
                ok, frame = cap.read()
                if not ok:
                    break

                if frame_index % stride != 0:
                    frame_index += 1
                    continue

                timestamp_sec = frame_index / fps
                # MediaPipe VIDEO mode requires strictly increasing timestamps.
                timestamp_ms = int(timestamp_sec * 1000)

                angle = None
                hip_y = None
                try:
                    landmarks = detector.landmarks_for_frame(frame, timestamp_ms)
                except Exception as exc:  # a bad frame shouldn't kill the run
                    logger.warning("pose detection failed on frame %s: %s", frame_index, exc)
                    landmarks = None

                if landmarks:
                    pa = detector.get_point(landmarks, a_name)
                    pb = detector.get_point(landmarks, b_name)
                    pc = detector.get_point(landmarks, c_name)

                    # Only trust the angle when all three joints are visible.
                    if all(detector.is_visible(p) for p in (pa, pb, pc)):
                        angle = detector.calculate_angle(pa, pb, pc)

                    hip = detector.get_point(landmarks, "LEFT_HIP")
                    if detector.is_visible(hip):
                        hip_y = hip.y

                analyzer.add_frame(angle, timestamp_sec, frame_index, hip_y=hip_y)
                last_ts = timestamp_sec
                analysed += 1
                frame_index += 1
        finally:
            detector.close()

        duration = last_ts if last_ts > 0 else (frame_index / fps if fps else 0.0)
        return analyzer.finalize(duration_sec=duration)

    finally:
        cap.release()
