"""Connects an upload to the engine: saves the file, runs the engine, and removes the temporary files.

The engine blocks while it works, so it runs on a worker thread to keep the server responsive.
"""

from typing import Optional

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.engine import pipeline
from app.engine.document_reader import EXTENSIONS as DOCUMENT_EXTENSIONS
from app.engine.media_reader import AUDIO_DEMUXERS, VIDEO_DEMUXERS, MediaFile
from app.engine.schemas import LectureResult
from app.services import job_upload_service
from app.utils.file_utils import temp_job_dir


async def process_video(file: UploadFile, title: Optional[str] = None, language: Optional[str] = None) -> LectureResult:
    with temp_job_dir() as job_dir:
        saved = await job_upload_service.save_upload(file, job_dir, list(VIDEO_DEMUXERS), "video")
        video = MediaFile(filename=saved.filename, path=saved.path, size=saved.size)
        return await run_in_threadpool(pipeline.video_to_notes, video, job_dir, title, language)


async def process_audio(file: UploadFile, title: Optional[str] = None, language: Optional[str] = None) -> LectureResult:
    with temp_job_dir() as job_dir:
        saved = await job_upload_service.save_upload(file, job_dir, list(AUDIO_DEMUXERS), "audio")
        audio = MediaFile(filename=saved.filename, path=saved.path, size=saved.size)
        return await run_in_threadpool(pipeline.audio_to_notes, audio, job_dir, title, language)


async def process_document(file: UploadFile, title: Optional[str] = None) -> LectureResult:
    with temp_job_dir() as job_dir:
        saved = await job_upload_service.save_upload(file, job_dir, DOCUMENT_EXTENSIONS, "document")
        return await run_in_threadpool(pipeline.document_to_notes, saved.path, saved.filename, saved.size, title)


async def process_text(text: str, title: Optional[str] = None) -> LectureResult:
    return await run_in_threadpool(pipeline.text_to_notes, text, title)
