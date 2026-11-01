"""Saving uploaded videos. The user's filename is never used as a path."""

import os
from pathlib import Path

from fastapi import UploadFile

from app.core import config
from app.core.errors import AppError
from app.engine.video_reader import DEMUXERS, VideoFile
from app.services.upload_service import CHUNK_SIZE, sanitize_filename


async def save_upload(file: UploadFile, job_dir: Path) -> VideoFile:
    """Check the extension, then stream the upload into job_dir under a fixed name."""
    filename = sanitize_filename(file.filename)
    extension = os.path.splitext(filename)[1].lower()
    if extension not in DEMUXERS:
        allowed = ", ".join(ext.lstrip(".").upper() for ext in DEMUXERS)
        raise AppError(415, "unsupported_file_type", f"Unsupported file type. Allowed video formats: {allowed}.")

    path = job_dir / f"video{extension}"
    size = 0
    with path.open("wb") as out:
        while chunk := await file.read(CHUNK_SIZE):
            size += len(chunk)
            if size > config.MAX_UPLOAD_SIZE_BYTES:
                limit_mb = config.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
                raise AppError(413, "file_too_large", f"File exceeds the maximum size of {limit_mb} MB.")
            out.write(chunk)

    if size == 0:
        raise AppError(400, "empty_file", "The uploaded file is empty.")
    return VideoFile(filename=filename, path=path, size=size)
