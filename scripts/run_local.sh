#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# One-command local setup + run for AthleteIQ.
#
# Live camera mode needs a "secure context": browsers only expose
# navigator.mediaDevices.getUserMedia on https:// or on http://localhost.
#
#   ./scripts/run_local.sh          -> http://localhost:8000   (laptop webcam)
#   ./scripts/run_local.sh --https  -> https://<your-LAN-IP>:8000 (phone camera)
#
# The --https mode generates a self-signed certificate so a phone on the same
# wifi gets a secure context and can therefore use its camera. Your browser
# will warn that the certificate is untrusted -- that is expected for a
# self-signed cert; click through it.
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$(pwd)"
USE_HTTPS=0
PORT="${PORT:-8000}"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

for arg in "$@"; do
  case "$arg" in
    --https) USE_HTTPS=1 ;;
    --port=*) PORT="${arg#*=}" ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
  esac
done

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

# ---- 1. Python environment -------------------------------------------------
if [ ! -d .venv ]; then
  echo "==> Creating virtualenv"
  $PY -m venv .venv
fi
VENV_PY=".venv/bin/python"
[ -f "$VENV_PY" ] || VENV_PY=".venv/Scripts/python.exe"   # Windows/Git Bash

echo "==> Installing Python dependencies"
"$VENV_PY" -m pip install -q --upgrade pip
"$VENV_PY" -m pip install -q -r requirements.txt

# ---- 2. AI model -----------------------------------------------------------
echo "==> Ensuring pose model is present"
"$VENV_PY" scripts/download_model.py

# ---- 3. Frontend -----------------------------------------------------------
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found. Install Node.js 18+ and re-run."
  exit 1
fi

if [ ! -d frontend/node_modules ]; then
  echo "==> Installing frontend dependencies (first run, takes a minute)"
  (cd frontend && npm ci --silent)
fi

echo "==> Copying MediaPipe web runtime for live mode"
bash scripts/setup_live.sh >/dev/null
echo "    done"

echo "==> Building the frontend"
(cd frontend && npm run build --silent)

# ---- 5. Serve --------------------------------------------------------------
# A stable secret means logins survive restarts.
if [ -z "${SECRET_KEY:-}" ]; then
  export SECRET_KEY="$("$VENV_PY" -c 'import secrets; print(secrets.token_urlsafe(48))')"
fi

LAN_IP="$(
  { ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+'; } \
  || { ipconfig getifaddr en0 2>/dev/null; } \
  || { hostname -I 2>/dev/null | awk '{print $1}'; } \
  || echo "127.0.0.1"
)"

echo
if [ "$USE_HTTPS" = "1" ]; then
  CERT_DIR="$ROOT/.certs"
  mkdir -p "$CERT_DIR"
  if [ ! -f "$CERT_DIR/cert.pem" ]; then
    echo "==> Generating a self-signed certificate for $LAN_IP"
    openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
      -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" \
      -subj "/CN=$LAN_IP" \
      -addext "subjectAltName=IP:$LAN_IP,IP:127.0.0.1,DNS:localhost" \
      >/dev/null 2>&1
  fi
  echo "======================================================================"
  echo "  AthleteIQ is starting with HTTPS"
  echo
  echo "  On this computer :  https://localhost:$PORT"
  echo "  On your phone    :  https://$LAN_IP:$PORT      <- same wifi"
  echo
  echo "  Your browser will warn about the self-signed certificate."
  echo "  Click Advanced -> Proceed. That is required for camera access."
  echo
  echo "  Then open  /live  and press 'Enable camera & start'."
  echo "======================================================================"
  echo
  exec "$VENV_PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" \
    --ssl-keyfile "$CERT_DIR/key.pem" --ssl-certfile "$CERT_DIR/cert.pem"
else
  echo "======================================================================"
  echo "  AthleteIQ is starting"
  echo
  echo "  Open:  http://localhost:$PORT"
  echo "  Live camera works here because localhost is a secure context."
  echo
  echo "  To use your PHONE's camera instead, stop this and run:"
  echo "      ./scripts/run_local.sh --https"
  echo
  echo "  Create an account from the Sign up page to get started."
  echo "======================================================================"
  echo
  exec "$VENV_PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
fi
