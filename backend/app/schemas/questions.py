"""Pydantic models for the question generation endpoint."""

from typing import Optional

from pydantic import BaseModel, Field

from app.engine.question_generator import QuestionChoice
from app.engine.schemas import Question

MAX_QUESTIONS = 50
MAX_INSTRUCTIONS_LENGTH = 1000


class QuestionRequest(BaseModel):
    transcript: str
    count: int = Field(ge=1, le=MAX_QUESTIONS)
    question_type: QuestionChoice
    instructions: Optional[str] = Field(default=None, max_length=MAX_INSTRUCTIONS_LENGTH)


class QuestionData(BaseModel):
    questions: list[Question]


class QuestionResponse(BaseModel):
    success: bool = True
    message: str
    data: QuestionData
