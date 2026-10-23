"""
Central application settings.

Everything that used to be hardcoded (secret key, DB URL, upload dir)
now comes from environment variables with sane development defaults.
Create a .env file to override any of these in production.
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


class Settings:
    # --- Security -------------------------------------------------------
    # BUGFIX: was a hardcoded literal in auth.py. Now env-driven; falls back
    # to a random per-boot key in dev so tokens are never signed with a
    # publicly known secret.
    SECRET_KEY: str = _env("SECRET_KEY", "").strip() or secrets.token_urlsafe(48)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_env("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in _env(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    # --- Database -------------------------------------------------------
    DATABASE_URL: str = _env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'sports_talent.db'}")

    # --- Uploads --------------------------------------------------------
    UPLOAD_DIR: Path = Path(_env("UPLOAD_DIR", str(BASE_DIR / "uploads")))
    MAX_UPLOAD_MB: int = int(_env("MAX_UPLOAD_MB", "80"))
    ALLOWED_VIDEO_EXT: set[str] = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

    # --- AI -------------------------------------------------------------
    POSE_MODEL_PATH: Path = Path(
        _env("POSE_MODEL_PATH", str(BASE_DIR / "app" / "ai" / "models" / "pose_landmarker_lite.task"))
    )
    # Analyse at most this many frames per video (keeps CPU inference quick).
    MAX_FRAMES: int = int(_env("MAX_FRAMES", "900"))

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
