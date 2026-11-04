"""Application settings, read once from environment variables (and an optional .env file)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer, got {value!r}") from exc


ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
MAX_UPLOAD_SIZE_BYTES = _int_env("MAX_UPLOAD_SIZE_MB", 500) * 1024 * 1024
MAX_TEXT_LENGTH = _int_env("MAX_TEXT_LENGTH", 200_000)
UPLOAD_DIR = BACKEND_DIR / os.getenv("UPLOAD_DIR", "storage/uploads")

MAX_VIDEO_DURATION_SECONDS = _int_env("MAX_VIDEO_MINUTES", 15) * 60
MAX_AUDIO_DURATION_SECONDS = _int_env("MAX_AUDIO_MINUTES", 30) * 60
MAX_DOCUMENT_PAGES = _int_env("MAX_DOCUMENT_PAGES", 300)  # pages of a PDF, or slides of a PowerPoint file
TEMP_DIR = BACKEND_DIR / os.getenv("TEMP_DIR", "temp")

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "") or "gemini-3.8-flash"
# Tried in order when the main model is overloaded or times out. Comma-separated; empty turns this off.
GEMINI_FALLBACK_MODELS = [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash").split(",") if m.strip()]

# Meeting integrations. The storage is for development only: see app/meetings/session_store.py.
MEETINGS_STORAGE_DIR = BACKEND_DIR / os.getenv("MEETINGS_STORAGE_DIR", "storage/meetings")
# Until LectureAI has logins, every request acts as this one local teacher.
DEV_USER_ID = os.getenv("DEV_USER_ID", "local-teacher")

# Where the browser reaches this API and the frontend. Sign-in providers send teachers back to these.
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Google Meet: a "Web application" OAuth client from Google Cloud. The secret must stay on the server.
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
