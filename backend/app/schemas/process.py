"""Pydantic models for the endpoints that turn a lecture into notes."""

from typing import Optional

from pydantic import BaseModel, Field

from app.engine.gemini_client import MAX_TRANSCRIPT_CHARACTERS
from app.engine.schemas import LectureResult

MIN_TEXT_LENGTH = 30


class TextProcessRequest(BaseModel):
    text: str = Field(min_length=MIN_TEXT_LENGTH, max_length=MAX_TRANSCRIPT_CHARACTERS)
    title: Optional[str] = None


class ProcessResponse(BaseModel):
    success: bool = True
    message: str
    data: LectureResult
