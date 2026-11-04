"""Saving an upload into a job's temporary folder. The user's filename is never used as a path."""

import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core import config
from app.core.errors import AppError
from app.services.upload_service import CHUNK_SIZE, sanitize_filename


@dataclass(frozen=True)
class SavedUpload:
    filename: str  # cleaned-up original name, for display only
    path: Path
    size: int


async def save_upload(file: UploadFile, job_dir: Path, extensions: list[str], kind: str) -> SavedUpload:
    """Check the extension, then stream the upload into job_dir as upload<extension>."""
    filename = sanitize_filename(file.filename)
    extension = os.path.splitext(filename)[1].lower()
    if extension not in extensions:
        allowed = ", ".join(ext.lstrip(".").upper() for ext in extensions)
        raise AppError(415, "unsupported_file_type", f"Unsupported file type. Allowed {kind} formats: {allowed}.")

    # A fixed name that can't clash with the engine's own files, such as audio.wav.
    path = job_dir / f"upload{extension}"
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
    return SavedUpload(filename=filename, path=path, size=size)
