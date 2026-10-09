"""Reusable authentication and role-authorization dependencies."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, UserRole


bearer_scheme = HTTPBearer(auto_error=False)


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the active user from a verified access token."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _authentication_error()
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as error:
        # PyJWT token errors are intentionally collapsed into one safe response.
        raise _authentication_error() from error

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise _authentication_error()
    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Build a dependency that permits only the supplied current-user roles."""

    if not allowed_roles:
        raise ValueError("At least one allowed role is required.")
    allowed = set(allowed_roles)

    def role_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return role_dependency
