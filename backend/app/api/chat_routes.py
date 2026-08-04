"""HTTP endpoint for local retrieval-augmented meeting chat."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_chat_service
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import ChatService, LocalModelUnavailableError


router = APIRouter(tags=["chat"])
ChatServiceDependency = Annotated[ChatService, Depends(get_chat_service)]


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, service: ChatServiceDependency) -> ChatResponse:
    """Answer a question using local retrieval over one meeting's transcript."""
    try:
        answer = service.answer_question(
            meeting_id=request.meeting_id, question=request.question
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LocalModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return ChatResponse(answer=answer)
