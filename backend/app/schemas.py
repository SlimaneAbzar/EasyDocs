from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    page_count: int
    uploaded_at: datetime


class QuestionRequest(BaseModel):
    question: str
    session_id: int | None = None


class SourceInfo(BaseModel):
    page_number: int
    text_excerpt: str


class AnswerResponse(BaseModel):
    answer: str
    language: str
    sources: list[SourceInfo]
    session_id: int | None = None


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    title: str
    created_at: datetime


class ChatSessionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    title: str
    created_at: datetime
    filename: str
    messages: list["SessionMessage"]


class SessionMessage(BaseModel):
    question: str
    answer: str
    asked_at: datetime


class QueryHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    filename: str
    session_id: int | None
    question: str
    answer: str
    language: str | None
    asked_at: datetime
