"""Authentication request and token response schemas."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.security import normalize_email


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int = Field(gt=0)
