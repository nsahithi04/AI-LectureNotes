"""What the engine takes in and returns. The API sends these to the client as JSON."""

from pydantic import BaseModel


class VideoInfo(BaseModel):
    filename: str
    duration: float  # seconds
    size: int        # bytes


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
    video: VideoInfo
    transcription: Transcript
    lecture_notes: GeneratedNotes
