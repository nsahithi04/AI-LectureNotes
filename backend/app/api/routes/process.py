"""HTTP endpoints that turn a lecture into notes. They only read the request and call the pipeline."""

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.process import ProcessResponse, TextProcessRequest
from app.services import pipeline_service

router = APIRouter(prefix="/api", tags=["process"])

MESSAGE = "Lecture notes generated successfully"


@router.post("/video/process", response_model=ProcessResponse)
async def process_video(
    video: UploadFile = File(...),
    title: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
) -> ProcessResponse:
    """Turn a lecture video into a transcript and structured lecture notes."""
    return ProcessResponse(message=MESSAGE, data=await pipeline_service.process_video(video, title, language))


@router.post("/audio/process", response_model=ProcessResponse)
async def process_audio(
    audio: UploadFile = File(...),
    title: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
) -> ProcessResponse:
    """Turn a lecture recording into a transcript and structured lecture notes."""
    return ProcessResponse(message=MESSAGE, data=await pipeline_service.process_audio(audio, title, language))


@router.post("/document/process", response_model=ProcessResponse)
async def process_document(document: UploadFile = File(...), title: Optional[str] = Form(None)) -> ProcessResponse:
    """Turn a PDF, Word (.docx) or PowerPoint (.pptx) file, such as slides or handouts, into structured lecture notes."""
    return ProcessResponse(message=MESSAGE, data=await pipeline_service.process_document(document, title))


@router.post("/text/process", response_model=ProcessResponse)
async def process_text(request: TextProcessRequest) -> ProcessResponse:
    """Turn pasted lecture text into structured lecture notes."""
    return ProcessResponse(message=MESSAGE, data=await pipeline_service.process_text(request.text, request.title))
