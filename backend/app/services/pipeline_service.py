"""Connects an upload to the engine: saves the file, runs the engine, and removes the temporary files."""

from typing import Optional

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.engine.pipeline import video_to_notes
from app.engine.schemas import LectureResult
from app.services import video_service
from app.utils.file_utils import temp_job_dir


async def process_video(
    file: UploadFile,
    title: Optional[str] = None,
    language: Optional[str] = None,
) -> LectureResult:
    with temp_job_dir() as job_dir:
        video = await video_service.save_upload(file, job_dir)
        # The engine blocks while it works, so it runs on a worker thread to keep the server responsive.
        return await run_in_threadpool(video_to_notes, video, job_dir, title, language)
