"""Extract a video's audio into a file you can listen to.

Run from the backend folder:  python -m scripts.extract_audio lecture.mp4 lecture.wav
"""

import sys
from pathlib import Path

from app.engine import audio_extractor
from app.engine.video_reader import DEMUXERS, VideoFile, inspect_video

video_path = Path(sys.argv[1]).expanduser()
output_path = Path(sys.argv[2]).expanduser()

video = VideoFile(filename=video_path.name, path=video_path, size=video_path.stat().st_size)
if video_path.suffix not in DEMUXERS:
    sys.exit(f"Unsupported file type. Allowed: {', '.join(DEMUXERS)}")

print(inspect_video(video))
print(audio_extractor.extract_audio(video.path, video.demuxer, output_path))
print(f"Saved {output_path}")
