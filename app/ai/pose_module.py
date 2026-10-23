"""
pose_module.py
--------------
Wraps MediaPipe Pose. Responsibility is only: turn a video frame into body
landmarks, and compute angles between them. Business logic (rep counting,
scoring) lives in exercise_detector.py.

BUGFIX: the original used `mp.solutions.pose`, the "legacy solutions" API.
That namespace was REMOVED in mediapipe 1.x, so both old pose files crashed
with `AttributeError: module 'mediapipe' has no attribute 'solutions'` the
moment they were imported. This is rewritten against the current
MediaPipe Tasks API (PoseLandmarker), which is the supported path.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from ..config import settings

# The Tasks API returns landmarks as a flat list. These indices match the
# 33-point BlazePose topology, same ordering the legacy PoseLandmark enum used.
POSE_LANDMARK_NAMES: list[str] = [
    "NOSE", "LEFT_EYE_INNER", "LEFT_EYE", "LEFT_EYE_OUTER", "RIGHT_EYE_INNER",
    "RIGHT_EYE", "RIGHT_EYE_OUTER", "LEFT_EAR", "RIGHT_EAR", "MOUTH_LEFT",
    "MOUTH_RIGHT", "LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_ELBOW",
    "RIGHT_ELBOW", "LEFT_WRIST", "RIGHT_WRIST", "LEFT_PINKY", "RIGHT_PINKY",
    "LEFT_INDEX", "RIGHT_INDEX", "LEFT_THUMB", "RIGHT_THUMB", "LEFT_HIP",
    "RIGHT_HIP", "LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE",
    "LEFT_HEEL", "RIGHT_HEEL", "LEFT_FOOT_INDEX", "RIGHT_FOOT_INDEX",
]
LANDMARK_INDEX: dict[str, int] = {n: i for i, n in enumerate(POSE_LANDMARK_NAMES)}


@dataclass
class Point:
    """A single landmark. Mirrors the old interface (.x/.y/.visibility)."""
    x: float
    y: float
    z: float = 0.0
    visibility: float = 0.0


class PoseDetector:
    """
    Thin wrapper over MediaPipe PoseLandmarker in VIDEO mode.

    Usage:
        with PoseDetector() as det:
            lms = det.landmarks_for_frame(bgr_frame, timestamp_ms)
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        detection_confidence: float = 0.6,
        tracking_confidence: float = 0.6,
    ):
        path = Path(model_path or settings.POSE_MODEL_PATH)
        if not path.exists():
            raise FileNotFoundError(
                f"Pose model not found at {path}. "
                "Run `python scripts/download_model.py` to fetch it."
            )
        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(path)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._closed = False

    # -- context manager so the native resources are always released --------
    def __enter__(self) -> "PoseDetector":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            try:
                self._landmarker.close()
            except Exception:
                pass  # native teardown can be noisy at interpreter shutdown
            self._closed = True

    # -- detection ----------------------------------------------------------
    def landmarks_for_frame(self, bgr_frame: np.ndarray, timestamp_ms: int) -> Optional[list[Point]]:
        """
        Run pose detection on one BGR (OpenCV) frame.
        Returns 33 Points, or None if no body was detected.
        """
        # OpenCV gives BGR; MediaPipe wants RGB.
        rgb = bgr_frame[:, :, ::-1].copy()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if not result.pose_landmarks:
            return None

        raw = result.pose_landmarks[0]
        # `visibility` exists on the Tasks landmarks but can be None.
        return [
            Point(
                x=lm.x,
                y=lm.y,
                z=getattr(lm, "z", 0.0) or 0.0,
                visibility=getattr(lm, "visibility", None) or 0.0,
            )
            for lm in raw
        ]

    # -- helpers (same names/semantics as the original) ---------------------
    @staticmethod
    def get_point(landmarks: Sequence[Point], landmark_name: str) -> Point:
        """Look a landmark up by name, e.g. 'LEFT_SHOULDER'."""
        try:
            return landmarks[LANDMARK_INDEX[landmark_name]]
        except KeyError as exc:
            raise KeyError(f"Unknown landmark '{landmark_name}'") from exc

    @staticmethod
    def is_visible(point: Point, threshold: float = 0.5) -> bool:
        """
        Guard against computing angles from joints that are off-screen or
        occluded, which would otherwise produce garbage rep counts.
        """
        return point.visibility >= threshold

    @staticmethod
    def calculate_angle(a: Point, b: Point, c: Point) -> float:
        """
        Angle a-b-c in degrees, with `b` as the vertex (elbow, knee, hip...).
        """
        radians = math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x)
        angle = abs(radians * 180.0 / math.pi)
        if angle > 180.0:
            angle = 360.0 - angle
        return angle
