import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from database import db_dependency
from model import User
from schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    oauth2_scheme,
    decode_access_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─────────────────────────────────────────────────────────
# POST /auth/register
# ─────────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(user_data: UserCreate, db: db_dependency):
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken",
        )

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ─────────────────────────────────────────────────────────
# POST /auth/login
# ─────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive a JWT access token",
)
def login(user_data: UserLogin, db: db_dependency):
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Generate JWT
    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return Token(access_token=token)


# ─────────────────────────────────────────────────────────
# GET /auth/me  (protected)
# ─────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
def get_me(token: str = Depends(oauth2_scheme), db: db_dependency = None):  # type: ignore[assignment]
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# ─────────────────────────────────────────────────────────
# POST /auth/forgot-password
# ─────────────────────────────────────────────────────────
@router.post(
    "/forgot-password",
    summary="Request a password reset token",
)
def forgot_password(request: ForgotPasswordRequest, db: db_dependency):
    user = db.query(User).filter(User.email == request.email).first()

    # Always return success to prevent user enumeration attacks
    if not user:
        return {
            "message": "If this email is registered, a reset token has been sent.",
            "reset_token": None,
        }

    # Generate a secure random token
    reset_token = secrets.token_urlsafe(32)
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)  # valid for 30 minutes

    user.reset_token = reset_token
    user.reset_token_expire = expire
    db.commit()

    # In production: send this token via email.
    # For now, we return it directly in the response for easy testing.
    return {
        "message": "Password reset token generated. In production this would be emailed.",
        "reset_token": reset_token,  # ← Remove this in production!
        "expires_in": "30 minutes",
    }


# ─────────────────────────────────────────────────────────
# POST /auth/reset-password
# ─────────────────────────────────────────────────────────
@router.post(
    "/reset-password",
    summary="Reset password using a valid reset token",
)
def reset_password(request: ResetPasswordRequest, db: db_dependency):
    # Find user with this token
    user = db.query(User).filter(User.reset_token == request.token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Check token expiry
    now = datetime.now(timezone.utc)
    if user.reset_token_expire is None or user.reset_token_expire.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one.",
        )

    # Update password and clear token
    user.hashed_password = hash_password(request.new_password)
    user.reset_token = None
    user.reset_token_expire = None
    db.commit()

    return {"message": "Password has been reset successfully. You can now login."}
