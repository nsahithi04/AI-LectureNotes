import ast
from pathlib import Path

import pytest

from app.core.errors import ENGINE_ERROR_STATUS
from app.engine import audio_extractor, gemini_client, notes_generator, question_generator, transcriber, video_reader
from app.engine.errors import EngineError

ENGINE_DIR = Path(audio_extractor.__file__).parent
ENGINE_FILES = sorted(ENGINE_DIR.glob("*.py"))


def imported_modules(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


@pytest.mark.parametrize("path", ENGINE_FILES, ids=lambda path: path.name)
def test_engine_stays_independent_of_the_web_app(path):
    forbidden = ("fastapi", "starlette", "app.api", "app.services", "app.repositories", "app.core.errors")
    assert not [module for module in imported_modules(path) if module.startswith(forbidden)]


def test_every_engine_error_has_an_http_status():
    codes = set()
    for module in (audio_extractor, gemini_client, notes_generator, question_generator, transcriber, video_reader):
        for node in ast.walk(ast.parse(Path(module.__file__).read_text())):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "EngineError":
                codes.add(node.args[0].value)

    assert codes
    assert codes == set(ENGINE_ERROR_STATUS)


def test_engine_errors_become_the_right_http_response(client, videos, monkeypatch):
    def fail(transcript, title=None):
        raise EngineError("gemini_rate_limited", "Try again later.")

    monkeypatch.setattr(notes_generator, "generate_notes", fail)

    with videos["mp4"].open("rb") as file:
        response = client.post("/api/video/process", files={"video": ("lecture.mp4", file)})

    assert response.status_code == 429
    assert response.json() == {"success": False, "error": {"code": "gemini_rate_limited", "message": "Try again later."}}
