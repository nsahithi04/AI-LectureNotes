"""Generate notes on their own, without the rest of the app.

Run from the backend folder:  python -m scripts.generate_notes lecture.wav [title]
It takes an audio file, or a .txt file that already holds a transcript.
"""

import sys
import time
from pathlib import Path

from app.engine import notes_generator, transcriber

source = Path(sys.argv[1]).expanduser()
title = sys.argv[2] if len(sys.argv) > 2 else None

if source.suffix == ".txt":
    transcript = source.read_text()
else:
    print("Transcribing...")
    transcript = transcriber.transcribe(source).text

print("Generating notes...")
started = time.monotonic()
notes = notes_generator.generate_notes(transcript, title)

print(notes.model_dump_json(indent=2))
print(f"\nTime taken: {time.monotonic() - started:.1f} seconds")
