"""Pydantic models for lectures. These define the JSON the frontend receives
(see frontend/src/types/lecture.ts for the matching TypeScript types)."""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class InputType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    PDF = "pdf"


class NoteType(str, Enum):
    DETAILED = "detailed"    # full transcript organized into topics, subtopics and body text
    SHORT = "short"          # main points per topic, for revision
    IMPORTANT = "important"  # key takeaways only, for skimming


class LectureStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Notes are a list of blocks: level-1 headings are topics, level-2 headings are subtopics.
class HeadingBlock(BaseModel):
    type: Literal["heading"] = "heading"
    level: Literal[1, 2]
    text: str


class ParagraphBlock(BaseModel):
    type: Literal["paragraph"] = "paragraph"
    text: str


class BulletsBlock(BaseModel):
    type: Literal["bullets"] = "bullets"
    items: list[str]


NoteBlock = Union[HeadingBlock, ParagraphBlock, BulletsBlock]


class LectureNotes(BaseModel):
    detailed: Optional[list[NoteBlock]] = None
    short: Optional[list[NoteBlock]] = None
    important: Optional[list[NoteBlock]] = None


class LectureSource(BaseModel):
    filename: Optional[str] = None
    file_size: Optional[int] = None
    characters: Optional[int] = None


class Lecture(BaseModel):
    """A lecture as returned by the API."""

    id: str
    title: str
    input_type: InputType
    status: LectureStatus
    note_types: list[NoteType]
    source: LectureSource
    notes: LectureNotes = Field(default_factory=LectureNotes)
    error: Optional[str] = None
    created_at: datetime


class LectureRecord(Lecture):
    """A lecture as stored by the app: the API fields plus internal ones that are never sent to the client."""
    file_path: Optional[str] = None  # where the uploaded file was saved
    text: Optional[str] = None       # the pasted text, for text inputs


class HealthResponse(BaseModel):
    status: str
    message: str
