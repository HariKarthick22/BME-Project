"""Input validation and HTML sanitization utilities."""
import html
import re
from typing import Any
from pydantic import BaseModel, Field, field_validator


def sanitize_string(v: Any) -> str:
    """Sanitize string by HTML escaping and limiting length."""
    if not isinstance(v, str):
        raise TypeError("String required")
    # HTML escape all user input to prevent XSS
    v = html.escape(v)
    v = v.strip()
    if len(v) > 10000:
        raise ValueError("String too long (max 10000 chars)")
    return v


def validate_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


class ChatMessageModel(BaseModel):
    """Validated chat message with HTML-escaped content."""

    content: str = Field(..., min_length=1, max_length=10000)
    user_id: str = Field(..., min_length=1, max_length=255)

    @field_validator("content", mode="before")
    @classmethod
    def sanitize_content(cls, v: Any) -> str:
        return sanitize_string(v)

    class Config:
        json_schema_extra = {
            "example": {
                "content": "What hospitals specialize in orthopedic surgery?",
                "user_id": "user_123",
            }
        }


class MedicalAnalysisRequest(BaseModel):
    """Validated medical analysis request with sanitized input."""

    text: str = Field(..., min_length=1, max_length=5000)
    request_type: str = Field(
        ..., pattern="^(diagnosis|entity|categorize)$"
    )  # Prevent injection

    @field_validator("text", mode="before")
    @classmethod
    def sanitize_text(cls, v: Any) -> str:
        return sanitize_string(v)

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Patient presents with chronic knee pain",
                "request_type": "diagnosis",
            }
        }
