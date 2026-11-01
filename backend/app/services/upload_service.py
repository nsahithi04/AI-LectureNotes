"""Validation and saving of uploaded lecture files.

Every upload is checked three ways (extension, the MIME type the browser reports, and the
file's first bytes), streamed to disk in chunks so large files never sit in memory, and
saved under a generated name: the user's filename is never used as a path.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core import config
from app.core.errors import AppError
from app.schemas.lecture import InputType

CHUNK_SIZE = 1024 * 1024  # 1 MB


@dataclass(frozen=True)
class FileFormat:
    input_type: InputType
    mime_types: frozenset[str]


FORMATS: dict[str, FileFormat] = {
    ".mp4": FileFormat(InputType.VIDEO, frozenset({"video/mp4"})),
    ".mov": FileFormat(InputType.VIDEO, frozenset({"video/quicktime"})),
    ".mp3": FileFormat(InputType.AUDIO, frozenset({"audio/mpeg", "audio/mp3"})),
    ".wav": FileFormat(InputType.AUDIO, frozenset({"audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"})),
    ".m4a": FileFormat(InputType.AUDIO, frozenset({"audio/mp4", "audio/x-m4a", "audio/m4a"})),
    ".pdf": FileFormat(InputType.PDF, frozenset({"application/pdf", "application/x-pdf"})),
}

# Browsers send a generic type for files they don't recognise; the content check still applies.
GENERIC_MIME_TYPES = {"", "application/octet-stream"}

# Top-level boxes that can start an MP4 / MOV / M4A file.
ISO_MEDIA_BOXES = {b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip", b"pnot"}


@dataclass(frozen=True)
class SavedFile:
    filename: str  # cleaned-up original name, for display only
    path: Path     # where the file was saved
    size: int


def allowed_formats(input_type: InputType) -> str:
    return ", ".join(ext.lstrip(".").upper() for ext, fmt in FORMATS.items() if fmt.input_type == input_type)


def sanitize_filename(raw: Optional[str]) -> str:
    """Reduce a client-supplied filename to a safe display name (no folders or odd characters)."""
    name = os.path.basename((raw or "").replace("\\", "/"))
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .")
    return name[:255] or "upload"


def _matches_signature(extension: str, header: bytes) -> bool:
    """Check the file's first bytes look like the format its extension claims."""
    if extension == ".mp3":
        # ID3 tag, or a bare MPEG audio frame
        return header.startswith(b"ID3") or (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0)
    if extension == ".wav":
        return header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    if extension == ".pdf":
        return header.startswith(b"%PDF-")
    if extension in {".mp4", ".mov", ".m4a"}:
        return header[4:8] in ISO_MEDIA_BOXES
    return False


def validate_file_type(input_type: InputType, file: UploadFile) -> tuple[str, str]:
    """Check the extension and MIME type. Returns (safe filename, extension)."""
    filename = sanitize_filename(file.filename)
    extension = os.path.splitext(filename)[1].lower()
    fmt = FORMATS.get(extension)

    if fmt is None:
        raise AppError(415, "unsupported_file_type", f"Unsupported file type. Allowed {input_type.value} formats: {allowed_formats(input_type)}.")
    if fmt.input_type != input_type:
        raise AppError(
            400,
            "input_mismatch",
            f"A {extension} file can't be uploaded as {input_type.value}. Choose the {fmt.input_type.value} input type instead.",
        )

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in fmt.mime_types and content_type not in GENERIC_MIME_TYPES:
        raise AppError(415, "unsupported_mime_type", f"MIME type {content_type!r} doesn't match a {extension} file.")
    return filename, extension


async def save_upload(input_type: InputType, file: UploadFile, lecture_id: str) -> SavedFile:
    """Validate an upload and stream it to UPLOAD_DIR as <lecture_id><extension>."""
    filename, extension = validate_file_type(input_type, file)
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = config.UPLOAD_DIR / f"{lecture_id}{extension}"

    size = 0
    header = b""
    try:
        with path.open("wb") as out:
            while chunk := await file.read(CHUNK_SIZE):
                if not header:
                    header = chunk[:16]
                size += len(chunk)
                if size > config.MAX_UPLOAD_SIZE_BYTES:
                    limit_mb = config.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
                    raise AppError(413, "file_too_large", f"File exceeds the maximum size of {limit_mb} MB.")
                out.write(chunk)

        if size == 0:
            raise AppError(400, "empty_file", "The uploaded file is empty.")
        if not _matches_signature(extension, header):
            raise AppError(415, "invalid_file_content", f"The file content doesn't look like a valid {extension} file.")
    except BaseException:
        # Never leave a partial or rejected file behind.
        path.unlink(missing_ok=True)
        raise

    return SavedFile(filename=filename, path=path, size=size)
