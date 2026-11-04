import io
import zipfile

import pytest

from app.core import config
from app.engine import document_reader
from tests.conftest import make_docx, make_pdf, make_pptx

SLIDE_1 = "Supervised learning uses labelled examples to train a model."
SLIDE_2 = "Overfitting means the model memorises its training data."

MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def upload(client, content, filename="slides.pdf", **form):
    mime = MIME_TYPES.get(filename.rsplit(".", 1)[-1], "application/octet-stream")
    return client.post("/api/document/process", files={"document": (filename, content, mime)}, data=form)


def error_code(response):
    return response.json()["error"]["code"]


def test_pdf_text_is_turned_into_notes(client, temp_dir):
    content = make_pdf([SLIDE_1, SLIDE_2])
    response = upload(client, content, title="Week 5")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"] == {
        "type": "document",
        "format": "pdf",
        "filename": "slides.pdf",
        "size": len(content),
        "duration": None,
        "pages": 2,
        "characters": len(data["text"]),
    }
    assert data["transcription"] is None
    assert data["text"] == f"{SLIDE_1}\n\n{SLIDE_2}"
    # The fake notes generator copies its input into the first section.
    assert data["lecture_notes"]["sections"][0]["content"] == data["text"]
    assert data["lecture_notes"]["title"] == "Week 5"
    assert list(temp_dir.iterdir()) == []


def test_word_document_text_and_tables_are_read(client, temp_dir):
    response = upload(client, make_docx([SLIDE_1, "", SLIDE_2], table_cells=["Term: bias", "Meaning: error from assumptions"]), "handout.docx")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"]["format"] == "docx"
    assert data["source"]["pages"] is None
    assert data["text"] == f"{SLIDE_1}\n\n{SLIDE_2}\n\nTerm: bias | Meaning: error from assumptions"
    assert list(temp_dir.iterdir()) == []


def test_powerpoint_slides_and_speaker_notes_are_read_in_order(client):
    content = make_pptx(
        [["Overfitting", SLIDE_2], ["Supervised learning", SLIDE_1]],
        notes={1: "Mention the exam question on this."},
        order=[2, 1],
    )
    response = upload(client, content, "lecture.pptx")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"]["format"] == "pptx"
    assert data["source"]["pages"] == 2
    assert data["text"] == (
        f"Slide 1\nSupervised learning\n{SLIDE_1}\n\n"
        f"Slide 2\nOverfitting\n{SLIDE_2}\nSpeaker notes: Mention the exam question on this."
    )


@pytest.mark.parametrize("filename", ["notes.doc", "slides.ppt", "notes.txt"])
def test_other_files_are_rejected(client, filename):
    response = upload(client, b"hello", filename)

    assert response.status_code == 415
    assert error_code(response) == "unsupported_file_type"
    assert "PDF, DOCX, PPTX" in response.json()["error"]["message"]


@pytest.mark.parametrize(
    "filename, content",
    [
        ("slides.pdf", b"%PDF-1.4 this is not really a pdf"),
        ("handout.docx", b"not a zip file"),
        ("lecture.pptx", make_docx([SLIDE_1])),  # a Word file renamed to .pptx
        ("handout.docx", make_pptx([[SLIDE_1]])),  # a PowerPoint file renamed to .docx
    ],
)
def test_damaged_or_renamed_documents_are_rejected(client, temp_dir, filename, content):
    response = upload(client, content, filename)

    assert response.status_code == 400
    assert error_code(response) == "invalid_document"
    assert list(temp_dir.iterdir()) == []


def test_xml_that_expands_too_far_is_rejected(client, monkeypatch):
    monkeypatch.setattr(document_reader, "MAX_XML_BYTES", 100)
    response = upload(client, make_docx([SLIDE_1, SLIDE_2]), "handout.docx")

    assert response.status_code == 400
    assert error_code(response) == "invalid_document"
    assert "too large" in response.json()["error"]["message"]


@pytest.mark.parametrize(
    "filename, content",
    [("slides.pdf", make_pdf(["", ""])), ("handout.docx", make_docx(["Hi"])), ("lecture.pptx", make_pptx([[], []]))],
)
def test_documents_without_text_are_rejected(client, filename, content):
    response = upload(client, content, filename)

    assert response.status_code == 422
    assert error_code(response) == "no_text"


@pytest.mark.parametrize(
    "filename, content",
    [("slides.pdf", make_pdf([SLIDE_1, SLIDE_2])), ("lecture.pptx", make_pptx([[SLIDE_1], [SLIDE_2]]))],
)
def test_documents_over_the_page_limit_are_rejected(client, monkeypatch, filename, content):
    monkeypatch.setattr(config, "MAX_DOCUMENT_PAGES", 1)
    response = upload(client, content, filename)

    assert response.status_code == 422
    assert error_code(response) == "document_too_long"


def test_xml_entity_expansion_is_refused(client):
    """A "billion laughs" file must fail safely instead of using up the server's memory."""
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaaaaaaaa">'
        + "".join(f'<!ENTITY {chr(98 + i)} "{("&" + chr(97 + i) + ";") * 10}">' for i in range(8))
        + ']><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>&i;</w:t></w:r></w:p></w:body></w:document>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", bomb)

    response = upload(client, buffer.getvalue(), "handout.docx")

    assert response.status_code == 400
    assert error_code(response) == "invalid_document"
