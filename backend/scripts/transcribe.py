"""Transcribe an audio file on its own, without the rest of the app.

Run from the backend folder:  python -m scripts.transcribe lecture.wav [language]
"""

import sys
import time
from pathlib import Path

from app.engine import transcriber

audio_path = Path(sys.argv[1]).expanduser()
language = sys.argv[2] if len(sys.argv) > 2 else None

started = time.monotonic()
transcript = transcriber.transcribe(audio_path, language)

print(transcript.text)
print(f"\nLanguage: {transcript.language}")
print(f"Segments: {len(transcript.segments)}")
print(f"Time taken: {time.monotonic() - started:.1f} seconds")
