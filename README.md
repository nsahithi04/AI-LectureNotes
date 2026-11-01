# LectureAI

Upload a lecture video and get structured notes and a timestamped transcript.

The MVP covers video only: **video → FFmpeg audio → faster-whisper transcript → Gemini notes → results screen**. There's no database or login yet, so notes aren't saved.

| Limit | Value |
| ----- | ----- |
| Formats | MP4, MOV, MKV |
| Length | 15 minutes |
| File size | 500 MB |

## Prerequisites

| Tool | Version | Check |
| ---- | ------- | ----- |
| Python | 3.12 | `python3.12 --version` |
| Node.js | 20.19 or newer | `node --version` |
| FFmpeg | Any recent version | `ffmpeg -version` |
| Gemini API key | Create one in [Google AI Studio](https://aistudio.google.com/apikey) | |

Use Python 3.12 for the backend, because the pinned speech-to-text packages may not work on newer versions.

Install FFmpeg, which also includes FFprobe:

```bash
brew install ffmpeg                # macOS
sudo apt install ffmpeg            # Ubuntu or Debian
```

## Setup

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # Windows: copy .env.example .env
```

Open `backend/.env` and set `GEMINI_API_KEY`. Never commit this file or share the key in chat. Each person on the team uses their own `.env`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env               # Windows: copy .env.example .env
```

## Running the app

Run each of these in its own terminal.

**Backend**, at http://127.0.0.1:8000 (API docs at http://127.0.0.1:8000/docs):

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --reload-dir app
```

`--reload-dir app` matters: without it, changes inside `.venv` can restart the server and cancel a video in progress.

**Frontend**, at http://localhost:5173:

```bash
cd frontend
npm run dev
```

## Uploading a lecture

1. Open http://localhost:5173/new. Use `localhost` here, because it's the address the backend allows.
2. Drop in a video, or click **browse files**.
3. Click **Generate Lecture Notes**.
4. Keep the tab open until the notes appear. A 15-minute lecture takes around 5 minutes on an M1 Pro, and longer when Gemini is slow.

The first run also downloads the Whisper model, which is about 500 MB.

## How the pipeline works

```
Browser ── POST /api/video/process ──► app/api/routes/video.py
                                         app/services/pipeline_service.py
                                           saves the upload to temp/<job id>/
                                           app/engine/pipeline.py  video_to_notes()
                                             1. video_reader.py      FFprobe checks the file
                                             2. audio_extractor.py   FFmpeg writes 16 kHz mono WAV
                                             3. transcriber.py       faster-whisper makes the transcript
                                             4. notes_generator.py   Gemini writes structured notes
                                           deletes temp/<job id>/, even after a failure
Browser ◄── JSON: video, transcription, lecture_notes
```

It's one long request, so there's no live progress. The upload is deleted as soon as the request ends.

## Project structure

```
lecture-ai/
├── frontend/src/
│   ├── pages/                  One file per screen
│   ├── components/             ui, layout, upload and lecture components
│   ├── services/api.ts         Every call to the backend
│   ├── types/lecture.ts        Types matching the API's JSON
│   └── utils/notes.ts          Turns the API's notes into the results tabs
└── backend/
    ├── app/
    │   ├── engine/             Video to notes, with no web code and no users
    │   ├── api/routes/         HTTP only
    │   ├── services/           Connects uploads to the engine
    │   ├── schemas/            API response shapes
    │   └── core/               Settings and JSON errors
    ├── scripts/                Run one engine step on its own
    └── tests/
```

**The engine rule:** `app/engine/` must not import the web framework or know about users, so any frontend or background worker can reuse it. `tests/test_engine.py` fails if this is broken.

The older `/api/lectures` routes, `LecturePage` and `NoteTypePicker` aren't used by the MVP.

## API

`POST /api/video/process` takes a multipart form:

| Field | Required | Meaning |
| ----- | -------- | ------- |
| `video` | Yes | The video file |
| `title` | No | Title to use for the notes. Gemini writes one if it's missing. |
| `language` | No | Language code such as `en` or `hi`. Whisper detects it if it's missing. |

```json
{
  "success": true,
  "message": "Lecture notes generated successfully",
  "data": {
    "video": { "filename": "lecture.mp4", "duration": 84.0, "size": 334723 },
    "transcription": {
      "language": "en",
      "text": "Welcome to today's lecture...",
      "segments": [{ "start": 0.0, "end": 2.4, "text": "Welcome to today's lecture." }]
    },
    "lecture_notes": {
      "title": "...",
      "overview": "...",
      "learning_objectives": ["..."],
      "sections": [
        {
          "heading": "...",
          "content": "...",
          "key_points": ["..."],
          "definitions": [{ "term": "...", "meaning": "..." }],
          "examples": ["..."]
        }
      ],
      "important_concepts": ["..."],
      "key_takeaways": ["..."],
      "conclusion": "..."
    }
  }
}
```

Errors always look like this:

```json
{ "success": false, "error": { "code": "video_too_long", "message": "Videos can be up to 15 minutes long." } }
```

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| "Could not reach the backend" | Start the backend, and make sure you opened `localhost:5173`, not `127.0.0.1:5173`. |
| `{"detail":"Not Found"}` on port 8000 | Something else, such as Docker, is answering. Start uvicorn and use `127.0.0.1:8000`, not `localhost:8000`. |
| `command not found: python` or `uvicorn` | Run `source .venv/bin/activate` inside `backend/`. |
| "Video processing isn't available on the server" | FFmpeg isn't installed, or isn't on your PATH. |
| "The notes service isn't set up on the server" | Set `GEMINI_API_KEY` in `backend/.env`, then restart the backend. |
| "The notes service has reached its usage limit" | Your Gemini quota has run out. Wait, or check your limits in Google AI Studio. |
| Generating takes far longer than usual, or "The notes service couldn't be reached" | Gemini may be overloaded. The backend tries 3 times, and each try can wait up to 3 minutes. Try again later, or set a different `GEMINI_MODEL` in `backend/.env`. |
| "This video has no audio" or "No speech was found" | The video has no usable speech to transcribe. |
| A long video fails after a few minutes in Safari | Use Chrome. Long requests haven't been tested in Safari. |
| The server restarts during a job | Start uvicorn with `--reload-dir app`. |
| `metadata_errors` error from Whisper | Run `pip install -r requirements.txt` to get the pinned `av` version. |

## Running the tests

Backend tests use fakes, so they never call Whisper or Gemini:

```bash
cd backend
source .venv/bin/activate
pytest
```

Frontend tests and checks:

```bash
cd frontend
npm test
npm run build
```

## Manual end-to-end test

Run this before merging changes to the pipeline. Each generated set of notes uses at least 1 Gemini request.

| # | Do this | Expect |
| - | ------- | ------ |
| 1 | Upload a `.txt` file | "Unsupported file type", and nothing is sent |
| 2 | Upload a video, then click **Remove** | The dropzone comes back |
| 3 | Upload a video with no speech | "No speech was found in this video.", and the file stays selected |
| 4 | Upload a video over 15 minutes | "Videos can be up to 15 minutes long." |
| 5 | Upload a real lecture and click **Generate Lecture Notes** | The loading screen appears, then the notes |
| 6 | Open each tab | Detailed notes, Short notes, Important points and Transcript all show content |
| 7 | Compare the notes with the lecture | Nothing is invented, and timestamps match the video |
| 8 | Click **Copy**, then paste | The text from the current tab appears |
| 9 | Refresh the page | The notes stay |
| 10 | Click **New lecture** | A clean upload page opens |
| 11 | Check `backend/temp/` | It holds only `.gitkeep` |

## What's next

1. Generate Q&A from the transcript in `app/engine/`.
2. Add a job queue, so a long video doesn't need one open request.
3. Choose a database, then add login and roles.
4. Add audio, PDF and text uploads.
5. When the application is done, split it into frontend, API and engine repositories.
