import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import models
from .config import settings
from .database import engine
from .routers import assessments, auth_router, leaderboard, scouts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# Creates tables if they don't exist. Use Alembic migrations in production.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AthliteIQ Sports Talent Assessment API",
    description=(
        "Backend for an AI-powered platform that democratizes sports talent "
        "assessment - athletes anywhere record standard fitness tests, get "
        "AI-scored results from real pose estimation, and appear on regional "
        "and national leaderboards visible to scouts."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All API routes live under /api so they can never collide with client-side
# SPA routes. Without this, a browser hitting /leaderboard matched the API
# endpoint and got a 422 instead of the React page.
API_PREFIX = "/api"
app.include_router(auth_router.router, prefix=API_PREFIX)
app.include_router(assessments.router, prefix=API_PREFIX)
app.include_router(leaderboard.router, prefix=API_PREFIX)
app.include_router(scouts.router, prefix=API_PREFIX)
app.include_router(scouts.meta_router, prefix=API_PREFIX)


@app.get("/api/health", tags=["Meta"])
def health():
    """Liveness probe. Also reports whether the AI model is installed."""
    return {
        "status": "ok",
        "message": "AthliteIQ Sports Talent Assessment API is running",
        "version": "2.0.0",
        "ai_model_present": settings.POSE_MODEL_PATH.exists(),
    }


# --------------------------------------------------------------- frontend --
# Serve the built React app. Mounted last so API routes always win.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.get("/api/frontend-status", include_in_schema=False)
def frontend_status():
    built = (FRONTEND_DIST / "index.html").exists()
    return {
        "status": "ok",
        "frontend_built": built,
        "message": (
            "Frontend is ready"
            if built
            else "Build the frontend with: cd frontend && npm.cmd run build"
        ),
    }


if FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

@app.get("/", include_in_schema=False)
def root_spa():
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        return FileResponse(FRONTEND_DIST / "index.html")
    return HTMLResponse(
        "<!doctype html><html><body><h1>AthliteIQ API is running</h1>"
        "<p>Build the frontend with <code>cd frontend && npm.cmd run build</code>.</p>"
        '<p><a href="/docs">Open API docs</a></p></body></html>'
    )


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    """
    SPA fallback: any non-API path returns the frontend shell, so client-side
    routing works on a hard refresh even when the bundle is not built yet.
    """
    if full_path.startswith("api"):
        return HTMLResponse("", status_code=404)
    if FRONTEND_DIST.exists():
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
    return HTMLResponse(
        "<!doctype html><html><body><h1>AthliteIQ API is running</h1>"
        "<p>Build the frontend with <code>cd frontend && npm.cmd run build</code>.</p>"
        '<p><a href="/docs">Open API docs</a></p></body></html>'
    )
