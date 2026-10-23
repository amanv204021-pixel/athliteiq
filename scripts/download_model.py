"""
Download the MediaPipe pose landmarker model used by the AI pipeline.

Usage:  python scripts/download_model.py
"""
import sys
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
DEST = Path(__file__).resolve().parent.parent / "app" / "ai" / "models" / "pose_landmarker_lite.task"


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size > 1_000_000:
        print(f"Model already present: {DEST} ({DEST.stat().st_size / 1e6:.1f} MB)")
        return 0
    print(f"Downloading pose model -> {DEST}")
    urllib.request.urlretrieve(MODEL_URL, DEST)
    print(f"Done: {DEST.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
