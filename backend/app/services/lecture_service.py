"""Creating and fetching lectures. The routes call these functions; they don't touch storage directly."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core import config
from app.core.errors import AppError
from app.repositories.lecture_repository import lecture_repository
from app.schemas.lecture import InputType, LectureRecord, LectureSource, LectureStatus, NoteType
from app.services.upload_service import save_upload

TITLE_MAX_WORDS = 8


def parse_input_type(raw: Optional[str]) -> InputType:
    try:
        return InputType((raw or "").strip().lower())
    except ValueError:
        allowed = ", ".join(t.value for t in InputType)
        raise AppError(400, "invalid_input_type", f"input_type must be one of: {allowed}.")


def parse_note_types(raw: list[str]) -> list[NoteType]:
    if not raw:
        raise AppError(400, "missing_note_types", "Choose at least one note type.")
    note_types: list[NoteType] = []
    for value in raw:
        try:
            note_type = NoteType(value.strip().lower())
        except ValueError:
            allowed = ", ".join(t.value for t in NoteType)
            raise AppError(400, "invalid_note_type", f"Unknown note type {value!r}. Allowed: {allowed}.")
        if note_type not in note_types:
            note_types.append(note_type)
    return note_types


def _title_from_text(text: str) -> str:
    words = text.split()
    title = " ".join(words[:TITLE_MAX_WORDS])
    return f"{title}..." if len(words) > TITLE_MAX_WORDS else title


def _title_from_filename(filename: str) -> str:
    words = Path(filename).stem.replace("_", " ").replace("-", " ").split()
    return " ".join(words) or "Untitled lecture"


async def create_lecture(
    raw_input_type: Optional[str],
    raw_note_types: list[str],
    text: Optional[str],
    file: Optional[UploadFile],
) -> LectureRecord:
    input_type = parse_input_type(raw_input_type)
    note_types = parse_note_types(raw_note_types)
    has_file = file is not None and bool(file.filename)
    has_text = bool(text and text.strip())

    lecture_id = uuid.uuid4().hex
    lecture = LectureRecord(
        id=lecture_id,
        title="",
        input_type=input_type,
        status=LectureStatus.UPLOADED,
        note_types=note_types,
        source=LectureSource(),
        created_at=datetime.now(timezone.utc),
    )

    if input_type == InputType.TEXT:
        if has_file:
            raise AppError(400, "input_mismatch", "A file was uploaded, but the input type is text.")
        cleaned = (text or "").strip()
        if not cleaned:
            raise AppError(400, "empty_text", "Text input can't be empty.")
        if len(cleaned) > config.MAX_TEXT_LENGTH:
            raise AppError(413, "text_too_long", f"Text exceeds the maximum length of {config.MAX_TEXT_LENGTH:,} characters.")
        lecture.text = cleaned
        lecture.title = _title_from_text(cleaned)
        lecture.source = LectureSource(characters=len(cleaned))
    else:
        if not has_file:
            raise AppError(400, "missing_file", f"No {input_type.value} file was uploaded.")
        if has_text:
            raise AppError(400, "input_mismatch", f"Text was sent, but the input type is {input_type.value}.")
        saved = await save_upload(input_type, file, lecture_id)
        lecture.file_path = str(saved.path)
        lecture.title = _title_from_filename(saved.filename)
        lecture.source = LectureSource(filename=saved.filename, file_size=saved.size)

    return lecture_repository.save(lecture)


def get_lecture(lecture_id: str) -> LectureRecord:
    lecture = lecture_repository.get(lecture_id)
    if lecture is None:
        raise AppError(404, "lecture_not_found", "Lecture not found.")
    return lecture


def list_lectures() -> list[LectureRecord]:
    return lecture_repository.list_all()
