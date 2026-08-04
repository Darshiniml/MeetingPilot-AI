"""HTTP contracts for local meeting chat."""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    meeting_id: int = Field(..., gt=0)
    question: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
