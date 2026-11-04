"""Asking Gemini for structured JSON. Every generator in the engine goes through here.

Gemini is told the exact shape to return, and the reply is still validated here. Incomplete or
malformed replies are retried, and are never returned to the caller. When a model is overloaded or
times out, the next try uses the next fallback model.
"""

import logging
import time
from collections.abc import Callable
from typing import Optional, TypeVar

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.core import config
from app.engine.errors import EngineError

logger = logging.getLogger(__name__)

# A 30-minute lecture is around 30,000 characters, so this only stops unexpected input.
MAX_TRANSCRIPT_CHARACTERS = 100_000
MAX_ATTEMPTS = 3
# Doubles after each failed try, so short spikes in demand have time to pass.
RETRY_DELAY_SECONDS = 2
REQUEST_TIMEOUT_MILLISECONDS = 120_000

Reply = TypeVar("Reply", bound=BaseModel)


def clean_transcript(transcript: str) -> str:
    transcript = transcript.strip()
    if not transcript:
        raise EngineError("empty_transcript", "There's no transcript to work from.")
    if len(transcript) > MAX_TRANSCRIPT_CHARACTERS:
        raise EngineError("transcript_too_long", "This lecture has too much text to process.")
    return transcript


def _handle_api_error(exc: genai_errors.APIError) -> None:
    """Raise for errors a retry can't fix. Returning means the request is worth trying again."""
    logger.error("Gemini request failed with status %s: %s", exc.code, exc.message)
    if exc.code == 429:
        raise EngineError("gemini_rate_limited", "The AI service has reached its usage limit. Try again later.") from exc
    if exc.code < 500:
        raise EngineError("gemini_unavailable", "The AI service isn't available on the server.") from exc


def _parse(text: Optional[str], schema: type[Reply], is_usable: Callable[[Reply], bool], attempt: int) -> Optional[Reply]:
    try:
        reply = schema.model_validate_json(text or "")
    except ValidationError:
        logger.warning("Gemini returned a malformed reply on attempt %s", attempt)
        return None
    if not is_usable(reply):
        logger.warning("Gemini returned an incomplete reply on attempt %s", attempt)
        return None
    return reply


def generate_json(
    prompt: str,
    system_instruction: str,
    schema: type[Reply],
    is_usable: Callable[[Reply], bool],
) -> Optional[Reply]:
    """Return a validated reply, or None if Gemini answered but never gave a usable one."""
    if not config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set")
        raise EngineError("gemini_not_configured", "The AI service isn't set up on the server.")

    client = genai.Client(
        api_key=config.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MILLISECONDS),
    )
    request_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0.2,
    )

    models = list(dict.fromkeys([config.GEMINI_MODEL, *config.GEMINI_FALLBACK_MODELS]))
    model_index = 0
    server_failed = False
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            time.sleep(RETRY_DELAY_SECONDS * 2 ** (attempt - 2))
        model = models[model_index]
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=request_config,
            )
        except genai_errors.APIError as exc:
            _handle_api_error(exc)
        except httpx.HTTPError as exc:
            logger.error("Could not reach Gemini: %s", exc)
        else:
            server_failed = False
            reply = _parse(response.text, schema, is_usable, attempt)
            if reply is not None:
                return reply
            continue

        server_failed = True
        if model_index + 1 < len(models):
            model_index += 1
            logger.warning("Gemini model %s failed, so the next try uses %s", model, models[model_index])

    if server_failed:
        raise EngineError("gemini_unavailable", "The AI service couldn't be reached. Try again in a moment.")
    return None
