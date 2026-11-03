"""One error type for the whole app, and handlers that turn every error into the same JSON shape:

    {"success": false, "error": {"code": "...", "message": "..."}}
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.engine.errors import EngineError

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Raise this from services to send a specific HTTP status and message to the client."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


# The HTTP status for each engine error. Any code not listed here is sent as a 500.
ENGINE_ERROR_STATUS = {
    "invalid_video": 400,
    "unsupported_language": 400,
    "no_audio": 422,
    "video_too_long": 422,
    "empty_transcript": 422,
    "transcript_too_long": 422,
    "gemini_rate_limited": 429,
    "audio_extraction_failed": 500,
    "transcription_failed": 500,
    "invalid_notes": 502,
    "invalid_questions": 502,
    "ffmpeg_missing": 503,
    "whisper_unavailable": 503,
    "gemini_not_configured": 503,
    "gemini_unavailable": 503,
}


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(EngineError)
    async def handle_engine_error(_: Request, exc: EngineError) -> JSONResponse:
        return error_response(ENGINE_ERROR_STATUS.get(exc.code, 500), exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", []) if part not in ("body", "path", "query"))
        message = f"{field}: {first.get('msg')}" if field else "Invalid request."
        return error_response(422, "invalid_request", message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return error_response(500, "internal_error", "An unexpected error occurred.")
