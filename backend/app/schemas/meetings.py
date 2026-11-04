"""Request and response shapes for the meeting endpoints."""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

from app.meetings.schemas import ProviderId

Data = TypeVar("Data")


class MeetingResponse(BaseModel, Generic[Data]):
    success: bool = True
    data: Data


class Connection(BaseModel):
    provider: ProviderId
    connected: bool
    account: Optional[str] = None  # the connected account's email address, when the provider shares it


class NotesRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
