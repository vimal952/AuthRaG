from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime


# Auth
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# Documents
class DocumentUploadMeta(BaseModel):
    title: str
    access_level: Literal["admin", "employee", "all"]


# Chat
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    sources: Optional[list[dict]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Admin
class RoleUpdateRequest(BaseModel):
    role: Literal["user", "employee", "admin"]
