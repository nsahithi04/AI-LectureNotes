"""What the engine takes in and returns. The API sends these to the client as JSON."""

from typing import Literal, Optional

from pydantic import BaseModel


SourceType = Literal["video", "audio", "document", "text"]


class SourceInfo(BaseModel):
    """What the notes were made from. Fields that don't apply to a source type are null."""

    type: SourceType
    format: Optional[str] = None        # file extension without the dot, such as mp4, pdf or pptx
    filename: Optional[str] = None
    size: Optional[int] = None          # bytes
    duration: Optional[float] = None    # seconds, for video and audio
    pages: Optional[int] = None         # pages of a PDF, or slides of a PowerPoint file
    characters: int = 0                 # length of the text the notes were made from


class AudioInfo(BaseModel):
    sample_rate: int
    channels: int
    size: int  # bytes


class TranscriptSegment(BaseModel):
    start: float  # seconds
    end: float    # seconds
    text: str


class Transcript(BaseModel):
    language: str
    text: str
    segments: list[TranscriptSegment]


class Definition(BaseModel):
    term: str
    meaning: str


class NoteSection(BaseModel):
    heading: str
    content: str
    key_points: list[str]
    definitions: list[Definition]
    examples: list[str]


class GeneratedNotes(BaseModel):
    title: str
    overview: str
    learning_objectives: list[str]
    sections: list[NoteSection]
    important_concepts: list[str]
    key_takeaways: list[str]
    conclusion: str


class LectureResult(BaseModel):
    source: SourceInfo
    transcription: Optional[Transcript] = None  # only for video and audio
    text: str                                   # the text the notes were made from
    lecture_notes: GeneratedNotes


class Question(BaseModel):
    type: Literal["multiple_choice", "short_answer"]
    topic: str
    question: str
    options: list[str]  # empty for short answer questions
    answer: str         # the correct option, or the ideal short answer


class GeneratedQuestions(BaseModel):
    questions: list[Question]
