"""HTTP endpoint for video processing. It only reads the request and calls the pipeline."""

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.video import VideoProcessResponse
from app.services import pipeline_service

router = APIRouter(prefix="/api/video", tags=["video"])


@router.post("/process", response_model=VideoProcessResponse)
async def process_video(
    video: UploadFile = File(...),
    title: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
) -> VideoProcessResponse:
    """Turn a lecture video into a transcript and structured lecture notes."""
    data = await pipeline_service.process_video(video, title, language)
    return VideoProcessResponse(message="Lecture notes generated successfully", data=data)
