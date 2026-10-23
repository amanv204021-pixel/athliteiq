#!/usr/bin/env bash
# Copy the MediaPipe web runtime + pose model into frontend/public so live
# camera mode works with no CDN and no external network.
#
# These files are derived from node_modules and the downloaded model, so they
# are gitignored rather than committed (~40 MB).
#
# Usage:  bash scripts/setup_live.sh     (run after `npm install`)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_WASM="$ROOT/frontend/node_modules/@mediapipe/tasks-vision/wasm"
DEST="$ROOT/frontend/public/mediapipe"
MODEL="$ROOT/app/ai/models/pose_landmarker_lite.task"

if [ ! -d "$SRC_WASM" ]; then
  echo "ERROR: @mediapipe/tasks-vision not installed."
  echo "Run:  cd frontend && npm install"
  exit 1
fi

if [ ! -f "$MODEL" ]; then
  echo "Pose model missing, downloading it first..."
  python "$ROOT/scripts/download_model.py"
fi

mkdir -p "$DEST/wasm" "$DEST/models"
cp "$SRC_WASM"/* "$DEST/wasm/"
cp "$MODEL" "$DEST/models/"

echo "Live mode assets ready:"
du -sh "$DEST/wasm" "$DEST/models"
