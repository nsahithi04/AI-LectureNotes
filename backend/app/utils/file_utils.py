"""Temporary files for one processing job. Everything goes in one folder, so cleanup can't miss a file."""

import shutil
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core import config


@contextmanager
def temp_job_dir() -> Iterator[Path]:
    """Create a unique folder under TEMP_DIR, and delete it afterwards even if processing fails."""
    job_dir = config.TEMP_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True)
    try:
        yield job_dir
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
