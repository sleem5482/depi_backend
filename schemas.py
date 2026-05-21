from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ── Register ──────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["john_doe"])
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., min_length=6, examples=["secret123"])


# ── Login ──────────────────────────────────────────────────
class UserLogin(BaseModel):
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., examples=["secret123"])


# ── Safe user response (no password) ──────────────────────
class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Token response ─────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


# ── Forgot Password ────────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., examples=["john@example.com"])


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., examples=["<paste-reset-token-here>"])
    new_password: str = Field(..., min_length=6, examples=["newSecret123"])
