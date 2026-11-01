"""Pydantic models for the video processing endpoint."""

from pydantic import BaseModel

from app.engine.schemas import LectureResult


class VideoProcessResponse(BaseModel):
    success: bool = True
    message: str
    data: LectureResult
