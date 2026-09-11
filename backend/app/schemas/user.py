"""User request and response Pydantic validation schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user properties."""

    email: EmailStr
    username: str = Field(
        ..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$"
    )


class UserCreate(UserBase):
    """Payload required to register a new user account."""

    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="student", pattern=r"^(student|instructor|admin)$")


class UserLogin(BaseModel):
    """Payload required to authenticate."""

    username_or_email: str
    password: str


class UserResponse(UserBase):
    """Public user identity representation."""

    id: uuid.UUID
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT bearer token issuance schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
