"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    verify_password,
    verify_unknown_user_password,
)
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserProfileResponse


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate an active user and issue a short-lived access token."""

    user = db.scalar(select(User).where(func.lower(User.email) == payload.email))
    if user is None:
        verify_unknown_user_password(payload.password)
        raise _invalid_credentials()

    valid_password = verify_password(payload.password, user.password_hash)
    if not valid_password or not user.is_active:
        raise _invalid_credentials()

    access_token, expires_in = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Return the safe profile for the currently authenticated active user."""

    return UserProfileResponse.model_validate(current_user)
