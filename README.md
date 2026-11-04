# LectureAI

Upload a lecture and get structured notes, then turn them into a quiz for students.

| Input | Formats | Limit | How the text is found |
| ----- | ------- | ----- | --------------------- |
| Video | MP4, MOV, MKV | 15 minutes | FFmpeg extracts the audio, then faster-whisper transcribes it |
| Audio | MP3, WAV, M4A | 30 minutes | faster-whisper transcribes it |
| Document | PDF, Word (.docx), PowerPoint (.pptx) | 300 pages or slides | The text is read from the file, including tables and PowerPoint speaker notes. Scanned PDFs and old .doc and .ppt files aren't supported. |
| Text | Pasted text | 30 to 100,000 characters | Used as it is |

Every file can be up to 500 MB. Gemini then writes the notes. There's no database or login yet, so notes aren't saved.

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
2. Choose Video, Audio, Document or Text. Drop in a file or click **browse files**, or paste the text.
3. Click **Generate Lecture Notes**.
4. Keep the tab open until the notes appear. A 15-minute lecture takes around 5 minutes on an M1 Pro, and longer when Gemini is slow.

The first run also downloads the Whisper model, which is about 500 MB.

## Creating a quiz

After the notes appear, open the **Quiz** tab:

1. Choose how many questions (up to 50) and the type: multiple choice, Q&A or both.
2. Add any requests, such as more questions on one topic.
3. Click **Generate Questions**.
4. Untick the questions you don't want, edit them, or add your own. **Copy** copies the selected questions with their answers.
5. Optionally choose a deadline, and choose whether students see their marks or only "Response submitted".
6. Click **Create Google Form**, sign in with Google, and share the student link.
7. Click **Get results** to see each student's score, their answers, and who submitted late. **Download CSV** saves them for Excel or Google Sheets.

The form is created in the teacher's own Google account. Every student gets the same questions. The form asks for the student's name and shuffles each question's options.

Some things Google Forms doesn't let apps control:

- **Deadlines:** Google can't close a form on a schedule. The deadline is shown on the form, late answers are marked in the results, and the form closes when the teacher gets results after the deadline or clicks **Stop accepting answers**.
- **What students see:** with "Their marks", the form is a Google quiz that marks multiple choice answers and shows students their marks as soon as they submit. With "Response submitted", the form is a plain form with no answer key, so students only see "Your response has been recorded". LectureAI then marks the multiple choice answers in the results, and shows the ideal answer next to each Q&A answer.
- **Question order:** Google can't shuffle question order for apps. Teachers can turn on **Shuffle question order** under Settings → Presentation in Google Forms, and the app shows this step.
- **Q&A marks:** these appear in the results once the teacher has marked them in Google Forms.

Questions aren't saved yet, so they're lost if you refresh or leave the page. Created forms are remembered on this browser only, under **Your Google Forms** in the Quiz tab, and teachers need to sign in with the Google account that created the form to get results.

### Setting up Google Forms (once per project)

1. Open the [Google Cloud console](https://console.cloud.google.com/) and create a project, for example `LectureAI`.
2. Go to **APIs & Services → Library**, search for **Google Forms API**, and click **Enable**.
3. Go to **Google Auth Platform** (also called the OAuth consent screen) and click **Get started**. Enter the app name and your email, and choose **External** as the audience.
4. Under **Audience → Test users**, add the Google account of every teacher who will try it. While the app is in testing, only these accounts can sign in.
5. Under **Clients**, click **Create client** and choose **Web application**. Under **Authorized JavaScript origins**, add `http://localhost:5173` and `http://localhost`. You don't need a redirect URI.
6. Copy the **Client ID** into `frontend/.env`:

   ```bash
   VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   ```

7. Restart `npm run dev`.

The client ID is public, so it's safe in frontend code. Never put the **client secret** in the frontend or commit it. This setup doesn't need it.

When a teacher signs in, Google shows "Google hasn't verified this app" until the app passes Google's verification. Test users can click **Continue**. Before launch, the app needs a privacy policy and Google's review.

## How the pipeline works

```
Browser ── POST /api/{video,audio,document,text}/process ──► app/api/routes/process.py
             app/services/pipeline_service.py   saves an upload to temp/<job id>/
             app/engine/pipeline.py
               video:  media_reader.inspect_video → audio_extractor → transcriber → notes_generator
               audio:  media_reader.inspect_audio → audio_extractor → transcriber → notes_generator
               document: document_reader.read_document → notes_generator
               text:   notes_generator
             deletes temp/<job id>/, even after a failure
Browser ◄── JSON: source, transcription (video and audio only), text, lecture_notes
```

- **media_reader.py** checks the file with FFprobe, including its length.
- **audio_extractor.py** uses FFmpeg to write 16 kHz mono WAV.
- **transcriber.py** uses faster-whisper to make a timestamped transcript.
- **document_reader.py** reads PDFs with pypdf, and Word and PowerPoint files with Python's own ZIP and XML tools. It rejects password-protected and scanned PDFs, and Word or PowerPoint files whose XML would expand to an unreasonable size.
- **notes_generator.py** asks Gemini for structured notes.

It's one long request, so there's no live progress. The upload is deleted as soon as the request ends.

## Meeting integrations (in progress)

LectureAI imports meeting transcripts from Google Meet and Microsoft Teams **after the meeting ends**, and turns them into notes. The shared layer is in `backend/app/meetings/`: each provider's data is converted into one `TranscriptSegment` format before it reaches the AI engine, so the engine never depends on a provider. Teachers without a plan that includes transcripts can record the class on their computer and upload the file instead.

| Provider | Status | What the teacher needs |
| -------- | ------ | ---------------------- |
| Google Meet | **Built** (backend) | A Workspace plan with Meet transcripts (Education Plus, Teaching and Learning Upgrade, Business Standard or higher), and transcription turned on during the meeting. Google deletes transcript entries after 30 days. |
| Microsoft Teams | Planned | A Microsoft 365 plan with Teams transcription, and a tenant admin allowing transcript access through Microsoft Graph. |
| Zoom | Planned, later | A Pro or higher plan with cloud recording. Live transcripts through RTMS also need the Zoom Developer Pack. |

### Setting up Google Meet

1. In [Google Cloud Console](https://console.cloud.google.com/), in the project you use for Google Forms, open **APIs & Services → Library** and enable the **Google Meet REST API**.
2. Under **APIs & Services → OAuth consent screen → Data access**, add the scope `https://www.googleapis.com/auth/meetings.space.readonly`. While the app is in testing, add each teacher's Google account as a test user. Publishing to everyone needs Google's verification, because this scope is sensitive.
3. Open your **Web application** OAuth client under **Credentials** (the one Google Forms uses works) and add this to **Authorized redirect URIs**:
   `http://127.0.0.1:8000/api/meetings/google_meet/callback`
4. Put the client ID and secret in `backend/.env` as `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`, then restart the backend. The secret stays on the server and must never go in `frontend/.env`.

To try it before the frontend page exists, open `http://127.0.0.1:8000/api/meetings/google_meet/connect` in your browser and sign in. Afterwards, `GET /api/meetings/google_meet/meetings` lists your recent meetings. `POST /api/meetings/google_meet/meetings/{id}/import` imports one, and `POST /api/meetings/sessions/{session_id}/notes` makes notes from it.

Sessions, transcripts and OAuth tokens are stored as files in `backend/storage/meetings/` for **development only**. Real use needs a database with encrypted tokens and LectureAI logins. Until then, every request acts as one development teacher (`DEV_USER_ID`).

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
    │   ├── meetings/           Meeting providers, transcript intake and normalization
    │   ├── api/routes/         HTTP only
    │   ├── services/           Connects uploads to the engine
    │   ├── schemas/            API response shapes
    │   └── core/               Settings and JSON errors
    ├── scripts/                Run one engine step on its own
    └── tests/
```

**The engine rule:** `app/engine/` must not import the web framework or know about users, so any frontend or background worker can reuse it. `tests/test_engine.py` fails if this is broken.

The older `/api/lectures` routes, `LecturePage` and `NoteTypePicker` aren't used by the app.

## API

Each input has its own endpoint, and they all return the same shape:

| Endpoint | Body |
| -------- | ---- |
| `POST /api/video/process` | Multipart form: `video` file, optional `title` and `language` |
| `POST /api/audio/process` | Multipart form: `audio` file, optional `title` and `language` |
| `POST /api/document/process` | Multipart form: `document` file (.pdf, .docx or .pptx), optional `title` |
| `POST /api/text/process` | JSON: `{"text": "...", "title": "..."}`, with `title` optional |

`title` sets the title of the notes, and Gemini writes one if it's missing. `language` is a code such as `en` or `hi`, and Whisper detects it if it's missing.

```json
{
  "success": true,
  "message": "Lecture notes generated successfully",
  "data": {
    "source": { "type": "video", "format": "mp4", "filename": "lecture.mp4", "size": 334723, "duration": 84.0, "pages": null, "characters": 1290 },
    "transcription": {
      "language": "en",
      "text": "Welcome to today's lecture...",
      "segments": [{ "start": 0.0, "end": 2.4, "text": "Welcome to today's lecture." }]
    },
    "text": "Welcome to today's lecture...",
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

`POST /api/questions/generate` takes JSON and returns questions:

```json
{
  "transcript": "Welcome to today's lecture...",
  "count": 10,
  "question_type": "both",
  "instructions": "More questions on gradient descent"
}
```

`question_type` is `multiple_choice`, `short_answer` or `both`, and `instructions` is optional. Each question has `type`, `topic`, `question`, `options` (empty for short answers) and `answer`.

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
| "The AI service isn't set up on the server" or "API key not valid" | Set `GEMINI_API_KEY` in `backend/.env` to the key from Google AI Studio (it starts with `AIza`), then restart the backend. Changes to `.env` aren't picked up until it restarts. |
| "The AI service has reached its usage limit" | Your Gemini quota has run out. Wait, or check your limits in Google AI Studio. |
| Generating takes far longer than usual, or "The AI service couldn't be reached" | Gemini may be overloaded. The backend tries 3 times, waiting longer each time, and switches to the models in `GEMINI_FALLBACK_MODELS` when the main one is busy. Try again later, or change the models in `backend/.env`. To see which models your key can use, check Google AI Studio. |
| "Google Forms isn't set up yet" | Add `VITE_GOOGLE_CLIENT_ID` to `frontend/.env`, then restart `npm run dev`. |
| Google says "Access blocked" or "redirect_uri_mismatch" | Add `http://localhost:5173` and `http://localhost` as authorized JavaScript origins, and add the teacher as a test user. |
| "The Google Forms API isn't turned on" | Enable the Google Forms API in the same Google Cloud project as the client ID. |
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

1. Build our own test link, so each student can get a different set of questions. This was removed from Google Forms, which can't do it.
2. Add a job queue, so a long video doesn't need one open request.
3. Choose a database, then add login and roles.
4. Read scanned PDFs with OCR, and old .doc and .ppt files.
5. When the application is done, split it into frontend, API and engine repositories.
