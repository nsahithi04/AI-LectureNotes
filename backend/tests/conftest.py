import io
import subprocess
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.main import app
from app.engine.schemas import GeneratedNotes, Transcript, TranscriptSegment
from app.engine import notes_generator, transcriber


@pytest.fixture(autouse=True)
def temp_dir(tmp_path, monkeypatch):
    """Point TEMP_DIR at an empty folder so each test can check what was left behind."""
    folder = tmp_path / "temp"
    monkeypatch.setattr(config, "TEMP_DIR", folder)
    return folder


@pytest.fixture(autouse=True)
def fake_transcription(monkeypatch):
    """Tests never run the real model. Whisper's own behaviour is tested with a fake in test_transcription.py."""
    transcript = Transcript(language="en", text="Hello.", segments=[TranscriptSegment(start=0, end=1, text="Hello.")])
    monkeypatch.setattr(transcriber, "transcribe", lambda audio_path, language=None: transcript)


@pytest.fixture(autouse=True)
def fake_notes(monkeypatch):
    """Tests never call Gemini. Notes generation is tested with a fake client in test_notes.py."""
    real_generate_notes = notes_generator.generate_notes

    def generate_notes(transcript, title=None):
        return GeneratedNotes(
            title=title or "Generated title",
            overview="Overview.",
            learning_objectives=[],
            sections=[{"heading": "Topic", "content": transcript, "key_points": [], "definitions": [], "examples": []}],
            important_concepts=[],
            key_takeaways=[],
            conclusion="Conclusion.",
        )

    monkeypatch.setattr(notes_generator, "generate_notes", generate_notes)
    return real_generate_notes


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def make_video(path, audio=True):
    command = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=s=64x64:r=5:d=2"]
    if audio:
        command += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2"]
    command += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        command += ["-c:a", "aac"]
    subprocess.run([*command, str(path)], check=True)
    return path


def make_audio(path, seconds=2):
    command = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
    subprocess.run([*command, str(path)], check=True)
    return path


def make_pdf(page_texts):
    """A small, valid PDF with one line of selectable text on each page."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in page_texts:
        content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
        objects.append(f"<< /Length {len(content)} >>\nstream\n{content.decode()}\nendstream")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {len(objects)} 0 R >>")
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"

    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n{body}\nendobj\n".encode()
    xref = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    pdf += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return pdf


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def make_docx(paragraphs, table_cells=()):
    """A minimal Word document: paragraphs, then an optional one-row table."""
    body = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    if table_cells:
        cells = "".join(f"<w:tc><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:tc>" for text in table_cells)
        body += f"<w:tbl><w:tr>{cells}</w:tr></w:tbl>"
    return _zip({"word/document.xml": f'<w:document xmlns:w="{W_NS}"><w:body>{body}</w:body></w:document>'})


def make_pptx(slides, notes=None, order=None):
    """A minimal PowerPoint file. `order` lists slide numbers in presentation order, if it differs."""
    order = order or list(range(1, len(slides) + 1))
    files = {}
    ids = "".join(f'<p:sldId id="{255 + n}" r:id="rId{n}"/>' for n in order)
    files["ppt/presentation.xml"] = f'<p:presentation xmlns:p="{P_NS}" xmlns:r="{R_NS}"><p:sldIdLst>{ids}</p:sldIdLst></p:presentation>'
    rels = "".join(f'<Relationship Id="rId{n}" Type="{R_NS}/slide" Target="slides/slide{n}.xml"/>' for n in range(1, len(slides) + 1))
    files["ppt/_rels/presentation.xml.rels"] = f'<Relationships xmlns="{RELS_NS}">{rels}</Relationships>'
    for number, lines in enumerate(slides, start=1):
        paragraphs = "".join(f"<a:p><a:r><a:t>{line}</a:t></a:r></a:p>" for line in lines)
        files[f"ppt/slides/slide{number}.xml"] = f'<p:sld xmlns:p="{P_NS}" xmlns:a="{A_NS}"><p:txBody>{paragraphs}</p:txBody></p:sld>'
        if notes and notes.get(number):
            files[f"ppt/slides/_rels/slide{number}.xml.rels"] = (
                f'<Relationships xmlns="{RELS_NS}"><Relationship Id="rId1" Type="{R_NS}/notesSlide" '
                f'Target="../notesSlides/notesSlide{number}.xml"/></Relationships>'
            )
            files[f"ppt/notesSlides/notesSlide{number}.xml"] = (
                f'<p:notes xmlns:p="{P_NS}" xmlns:a="{A_NS}"><a:p><a:r><a:t>{notes[number]}</a:t></a:r></a:p>'
                f"<a:p><a:fld><a:t>{number}</a:t></a:fld></a:p></p:notes>"
            )
    return _zip(files)


@pytest.fixture(scope="session")
def audios(tmp_path_factory):
    folder = tmp_path_factory.mktemp("audios")
    return {kind: make_audio(folder / f"lecture.{kind}") for kind in ("mp3", "wav", "m4a")}


@pytest.fixture(scope="session")
def videos(tmp_path_factory):
    folder = tmp_path_factory.mktemp("videos")
    return {
        "mp4": make_video(folder / "lecture.mp4"),
        "mov": make_video(folder / "lecture.mov"),
        "mkv": make_video(folder / "lecture.mkv"),
        "silent": make_video(folder / "silent.mp4", audio=False),
    }
