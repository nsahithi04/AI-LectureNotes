"""HTTP endpoints for lectures. They only read the request and call the lecture service."""

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.lecture import Lecture
from app.services import lecture_service

router = APIRouter(prefix="/api/lectures", tags=["lectures"])


@router.post("", response_model=Lecture, status_code=201)
async def create_lecture(
    input_type: Optional[str] = Form(None),
    note_types: list[str] = Form(default_factory=list),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
) -> Lecture:
    """Upload a lecture (a file, or text) and choose which notes to generate."""
    return await lecture_service.create_lecture(input_type, note_types, text, file)


@router.get("", response_model=list[Lecture])
def list_lectures() -> list[Lecture]:
    return lecture_service.list_lectures()


@router.get("/{lecture_id}", response_model=Lecture)
def get_lecture(lecture_id: str) -> Lecture:
    return lecture_service.get_lecture(lecture_id)
