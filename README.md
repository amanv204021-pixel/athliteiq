# AthliteIQ — AI Sports Talent Assessment

A full-stack platform that democratizes sports talent assessment. Athletes
anywhere record standard fitness tests on a phone, get **AI-scored results
from real pose estimation**, and appear on regional and national leaderboards
that scouts can filter — no travel, no physical trials.

**Stack:** FastAPI + SQLAlchemy + MediaPipe (backend) · React + Vite (frontend) · SQLite (swappable for Postgres)

---

## Quick start

### Windows PowerShell

Prerequisites: Python 3.12 (3.11 also works), Node.js 22.12+ (or 20.19+), and npm. Run these
commands from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\download_model.py

Copy-Item .env.example .env
# Set a private signing key for this shell; do not commit .env.
$env:SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"

Set-Location frontend
npm.cmd ci
New-Item -ItemType Directory -Force -Path public\mediapipe\wasm, public\mediapipe\models | Out-Null
Copy-Item node_modules\@mediapipe\tasks-vision\wasm\* public\mediapipe\wasm -Recurse -Force
Copy-Item ..\app\ai\models\pose_landmarker_lite.task public\mediapipe\models\pose_landmarker_lite.task
npm.cmd run build
Set-Location ..

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open **http://localhost:8000**. If PowerShell blocks `npm`, use
`npm.cmd` as shown. The live camera uses actual MediaPipe pose detection; the
first run downloads a real model file and the browser runtime is served locally.

For Vite hot reload, keep the backend running in one terminal, then run in a
second PowerShell terminal:

```powershell
Set-Location frontend
npm.cmd run dev
```

Open **http://localhost:5173**. Vite proxies `/api` requests to
`http://127.0.0.1:8000`. To call an API hosted elsewhere, set
`VITE_API_BASE_URL` in `frontend/.env` and add the frontend origin to
`CORS_ORIGINS` in the root `.env`.

### macOS / Linux

```bash
./scripts/run_local.sh            # laptop webcam -> http://localhost:8000
./scripts/run_local.sh --https    # phone camera  -> https://<your-LAN-IP>:8000
```
The script creates a virtualenv, installs dependencies, downloads the pose
model, prepares the local browser runtime, builds the frontend, and starts the
server. It does not seed synthetic assessments.

### Why live camera needs localhost or HTTPS

Browsers only expose `getUserMedia` in a **secure context**. That means
`https://` or `http://localhost` — never a plain-HTTP LAN address, and never
an embedded iframe that wasn't granted camera permission. Use `--https` to
test from your phone over wifi; accept the self-signed certificate warning.

## Manual setup

```bash
# 1. Backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_model.py     # fetches the MediaPipe pose model (~6 MB)

# 2. Frontend
cd frontend && npm ci && cd ..
bash scripts/setup_live.sh           # copies the MediaPipe web runtime for live mode
cd frontend && npm run build && cd ..

# 3. Run (serves API *and* the built UI on one port)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** · API docs at **/docs**

### Deploy on Render

1. Push this project to a GitHub repository.
2. In Render, choose **New → Blueprint**, connect the repository, and apply
   the `render.yaml` blueprint.
3. Render builds the React app and MediaPipe assets, creates a PostgreSQL
   database, generates a private `SECRET_KEY`, and starts the FastAPI service.
4. Open the service's `onrender.com` URL. The health check is `/api/health`.

The included blueprint uses Render's free plans. Free web services can sleep
when idle, and free databases are temporary and have limited storage/retention.
Uploaded videos live on ephemeral service storage and can disappear after a
restart or redeploy. Use paid persistent storage/database plans and object
storage before relying on it for production data. Do not add `.env`, database
files, user uploads, or credentials to a public repository.

### Optional sample accounts and data

`python scripts/seed.py` creates demo users and generated sample scores for
exploring the leaderboard and scout portal. These records are **not real
camera or video analyses**; they are marked “sample data” in the UI. The app
does not run this automatically. For an actual assessment, create your own
account and use Live assessment or Submit a test.

| Role | Email | Password |
|---|---|---|
| Athlete | `aryan@demo.in` | `password123` |
| Scout | `scout@demo.in` | `password123` |

### Frontend dev mode (hot reload)

```bash
uvicorn app.main:app --port 8000      # terminal 1
cd frontend && npm run dev            # terminal 2 -> http://localhost:5173
```
Vite proxies `/api/*` to the backend, so the browser only ever talks to one origin.

---

## Assessment modes

**Live camera (realtime)** — open `/live`, pick an exercise, and the app counts
your reps *as you move*, with a skeleton overlay, live joint angles and form
cues. Pose estimation runs entirely **on your device** via MediaPipe's
WebAssembly build, so **your video never leaves your phone** — only the final
numbers are submitted. The browser asks for camera permission after you press
**Enable camera & start**. A local prerecorded clip can also be selected and
analysed through the same real pose model; results are labelled “local video.”

**Upload a video** — record first, upload, and the Python backend analyses it
server-side. Slower, but the server sees the actual footage, so it's the
higher-trust path.

---

## How it works

1. **Sign up** as an athlete or a scout.
2. **Choose Live assessment or upload a test video** (`POST /api/assessments/upload`).
   Uploaded files are validated
   and stored, and the request returns immediately with `status: "processing"`.
3. **AI analysis** runs in the background: OpenCV reads the video frame by
   frame, MediaPipe's PoseLandmarker extracts 33 body landmarks, joint angles
   drive a rep-counting state machine, and the result is scored on posture,
   balance, accuracy and speed.
4. **Integrity checks** flag suspicious submissions (body not visible,
   implausible rep rate, video too short) for scout review instead of
   publishing them straight to the leaderboard.
5. **Leaderboards** rank each athlete's *personal best*, filterable by state,
   district, gender and age.

---

## Project layout

```
app/
  main.py               entrypoint, CORS, routers, serves the React build
  config.py             env-driven settings (secret key, DB, upload limits)
  database.py           SQLAlchemy engine/session
  models.py             User, Assessment
  schemas.py            Pydantic request/response models
  auth.py               bcrypt hashing + JWT
  routers/
    auth_router.py      /api/auth/signup, /login, /me
    assessments.py      /api/assessments/upload, /me, /{id}
    leaderboard.py      /api/leaderboard, /states
    scouts.py           /api/scouts/*, /api/test-types, /api/stats
  ai/
    config.py           EXERCISE_CONFIG — declarative test definitions
    pose_module.py      MediaPipe Tasks wrapper (landmarks + angles)
    exercise_detector.py rep/hold state machine, scoring, feedback
    video_analyzer.py   video -> pose -> reps -> score pipeline
frontend/
  src/pages/            Home, Login, Signup, Dashboard, Upload, Live, Leaderboard, Scout
  src/live/
    exerciseConfig.js   JS mirror of the Python EXERCISE_CONFIG
    liveAnalyzer.js     realtime rep/hold state machine (mirrors the server)
    usePoseCamera.js    webcam + MediaPipe LIVE_STREAM hook
    drawPose.js         skeleton overlay renderer
  src/api.js            fetch wrapper (relative URLs only)
  public/mediapipe/     WASM runtime + model (gitignored, see setup_live.sh)
tests/                  API and AI state-machine regression tests
scripts/                download_model.py, seed.py
```

---

## Adding a new test/sport

Add one entry to `EXERCISE_CONFIG` in `app/ai/config.py`:

```python
"burpee": {
    "display_name": "Burpees",
    "type": "rep_based",
    "landmarks": ("LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE"),
    "up_angle": 160,
    "down_angle": 70,
    "unit": "reps",
    "higher_is_better": True,
},
```

No other file changes. The analyzer, the upload validator, the leaderboard
and the frontend dropdowns all read from this config.

---

## Bugs fixed in v2.0

| # | Bug | Effect |
|---|---|---|
| 1 | `passlib` + modern `bcrypt` raised `password cannot be longer than 72 bytes` | **Every signup returned 500** |
| 2 | `pydantic==2.7.1` couldn't build on Python 3.13 | `pip install` failed outright |
| 3 | `EmailStr` used but `email-validator` not in requirements | ImportError on boot |
| 4 | `mp.solutions` removed in MediaPipe 1.x | Both pose modules crashed on import |
| 5 | `exercise_detector.py` imported by nothing; API returned hardcoded mock scores | **The AI did nothing** |
| 6 | Only 2 of 11 configured exercises had any implementation | 9 tests unusable |
| 7 | `bad_form_count` incremented per *frame*, not per rep | Hundreds of false penalties per video |
| 8 | Accuracy score could exceed 100 (unclamped) | Invalid scores |
| 9 | Leaderboard always sorted `score DESC` | Time-based tests ranked backwards |
| 10 | Leaderboard returned one row per *attempt* | One athlete could fill the whole top 10 |
| 11 | Leaderboard included `NULL` scores | Serialization crash |
| 12 | Flagged/cheating submissions were leaderboard-eligible | Integrity hole |
| 13 | Upload had no type or size validation | Disk exhaustion, crash on non-video |
| 14 | Filename extension taken from user input | Crash on extensionless names |
| 15 | Failed analysis left rows on `"processing"` forever | No error surfaced |
| 16 | Any `test_type` string accepted, then silently scored 0 | Bad data |
| 17 | `int(user_id)` on a tampered JWT raised an unhandled error | 500 instead of 401 |
| 18 | `datetime.utcnow()` deprecated in Python 3.12+ | Warnings, naive datetimes |
| 19 | Email comparison case-sensitive | Duplicate accounts, login failures |
| 20 | Hardcoded `SECRET_KEY` in source | Forgeable tokens |
| 21 | `scout`/`admin` roles existed with no endpoints | Role unreachable |
| 22 | Duplicate `pose_module.py` in two places | Code drift |
| 23 | API routes shadowed SPA routes (`/leaderboard` → 422) | Broken deep links |

---

## Configuration

All via environment variables (or a `.env`):

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | random per boot | JWT signing — **set this in production** |
| `DATABASE_URL` | `sqlite:///./sports_talent.db` | Use `postgresql://…` in production |
| `UPLOAD_DIR` | `./uploads` | Where videos are stored |
| `MAX_UPLOAD_MB` | `80` | Upload size cap |
| `MAX_FRAMES` | `900` | Frame budget per video |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token lifetime |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed development origins, comma-separated |

---

## Tests

```bash
python -m pytest -q
```

---

## API endpoints

All API paths use the `/api` prefix. Interactive OpenAPI documentation is at
`/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness and pose model presence |
| GET | `/api/frontend-status` | Built frontend status |
| POST | `/api/auth/signup` | Create an athlete or scout account |
| POST | `/api/auth/login` | Exchange email/password for a bearer token |
| GET | `/api/auth/me` | Current account |
| GET | `/api/test-types` | Supported exercises and units |
| GET | `/api/stats` | Landing-page counts |
| POST | `/api/assessments/live` | Save on-device camera or local-video results |
| POST | `/api/assessments/upload` | Upload a video for server-side analysis |
| GET | `/api/assessments/me` | Assessment history for the signed-in user |
| GET | `/api/assessments/{id}` | Read a result |
| DELETE | `/api/assessments/{id}` | Delete an owned result and uploaded video |
| GET | `/api/leaderboard?test_type=squat` | Personal-best leaderboard |
| GET | `/api/leaderboard/states` | Available state filters |
| GET | `/api/scouts/athletes` | Scout-only athlete search |
| GET | `/api/scouts/flagged` | Scout-only review queue |

Authentication uses `Authorization: Bearer <token>` for protected endpoints.
The SQLite database is created automatically at `sports_talent.db` in the
project root; uploaded videos are stored under `uploads/` by default.

## Troubleshooting

- **`python` or `npm` is not recognized:** install Python 3.11/3.12 and Node.js
  22.12+ (or 20.19+) and npm,
  reopen PowerShell, and use `npm.cmd` if the PowerShell execution policy
  blocks `npm.ps1`.
- **Pose model not found:** run
  `.\.venv\Scripts\python.exe scripts\download_model.py` from the root.
- **Camera permission denied:** allow camera access for the page in browser
  site settings, close other apps using the webcam, and reload the page.
- **Camera API unavailable:** open `http://localhost:8000` on the same
  computer, or use HTTPS. Plain HTTP from a phone to a LAN IP is not a secure
  browser context.
- **Browser model/runtime cannot load:** re-run the MediaPipe asset copy steps
  above after `npm.cmd ci`; verify `frontend/public/mediapipe/wasm` and
  `frontend/public/mediapipe/models/pose_landmarker_lite.task` exist.
- **Frontend API request fails:** ensure the backend is running on port 8000.
  For separate origins, set `VITE_API_BASE_URL` and include the frontend's
  exact origin in `CORS_ORIGINS`.
- **Sample records appear:** accounts and random scores from `scripts/seed.py`
  are explicitly marked as sample data. They are not AI assessments.

## Measurement limitations

Repetition counting and feedback use joint-angle thresholds and state
transitions, not a trained sports-scoring model. Camera placement, visibility,
lighting, and exercise execution affect results. The vertical-jump estimate
is approximate. Live and local-video mode keep video on the device; the API
receives untrusted, bounded summary values. Uploaded video can be independently
analysed by the server. Results are coaching guidance, not medical advice.

## Scaling to production

- Swap SQLite for PostgreSQL (`DATABASE_URL` only).
- Move video storage to S3/GCS instead of local disk.
- Move AI inference to a Celery/RQ worker or a dedicated GPU service —
  `run_ai_analysis` in `routers/assessments.py` is the seam.
- Add Alembic migrations instead of `create_all`.
- Tighten CORS from `*` to your app's domain.
- Add rate limiting on the upload endpoint.
- Calibrate vertical-jump estimation against a known reference object in
  frame; the current pixel-based estimate is approximate.

---

## Note on live mode and trust

Live results are computed in the browser, so the server has no footage to
verify them against. `POST /api/assessments/live` therefore treats the payload
as untrusted: it re-derives the headline score from the raw rep count (a
client that inflates `score` is ignored), re-runs the integrity heuristics
server-side, bounds every field via Pydantic, and tags the row
`source: "live_camera"` so scouts can tell it apart from an uploaded video.

For competitive ranking, prefer uploaded videos. Live mode is best for
training and instant feedback.
