"""FastAPI entry point: creates the app, configures CORS and errors, and registers routes."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, lectures, meetings, process, questions
from app.core import config
from app.core.errors import error_response, register_error_handlers

app = FastAPI(title="LectureAI API", version="0.1.0")

# Allowance for multipart boundaries and the other form fields on top of the file itself.
MULTIPART_OVERHEAD_BYTES = 1024 * 1024


@app.middleware("http")
async def reject_oversized_requests(request: Request, call_next):
    """Reject requests whose declared size is already too large, before the body is read."""
    content_length = request.headers.get("content-length", "")
    if content_length.isdigit() and int(content_length) > config.MAX_UPLOAD_SIZE_BYTES + MULTIPART_OVERHEAD_BYTES:
        limit_mb = config.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        return error_response(413, "file_too_large", f"File exceeds the maximum size of {limit_mb} MB.")
    return await call_next(request)


# Added after the size check so it wraps it, and rejected requests still get CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(health.router)
app.include_router(lectures.router)
app.include_router(process.router)
app.include_router(questions.router)
app.include_router(meetings.router)
