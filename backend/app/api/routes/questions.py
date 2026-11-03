"""HTTP endpoint for quiz questions. It only reads the request and calls the engine."""

from fastapi import APIRouter

from app.engine.question_generator import generate_questions
from app.schemas.questions import QuestionData, QuestionRequest, QuestionResponse

router = APIRouter(prefix="/api/questions", tags=["questions"])


# A plain def, because FastAPI runs these on a worker thread and Gemini can take minutes to reply.
@router.post("/generate", response_model=QuestionResponse)
def create_questions(request: QuestionRequest) -> QuestionResponse:
    """Generate quiz questions from a lecture's transcript."""
    questions = generate_questions(request.transcript, request.count, request.question_type, request.instructions)
    return QuestionResponse(message="Questions generated successfully", data=QuestionData(questions=questions))
