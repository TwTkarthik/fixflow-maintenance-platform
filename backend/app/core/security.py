"""Password hashing and JWT helpers for FixFlow authentication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from jwt import InvalidTokenError

from app.core.config import (
    get_access_token_expire_minutes,
    get_jwt_algorithm,
    get_jwt_secret_key,
)


password_hasher = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = password_hasher.hash("fixflow-invalid-user-password")


def normalize_email(email: str) -> str:
    """Normalize and minimally validate an email address."""

    normalized = email.strip().lower()
    if not normalized or "@" not in normalized or normalized.startswith("@"):
        raise ValueError("A valid email address is required.")
    return normalized


def hash_password(password: str) -> str:
    """Hash a password with the recommended Argon2id configuration."""

    if not password:
        raise ValueError("Password cannot be empty.")
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without exposing hash-library errors."""

    if not password or not password_hash:
        return False
    try:
        return password_hasher.verify(password, password_hash)
    except (TypeError, ValueError):
        return False


def verify_unknown_user_password(password: str) -> bool:
    """Perform equivalent work for an unknown email without revealing it."""

    return verify_password(password, _DUMMY_PASSWORD_HASH)


def create_access_token(subject: int) -> tuple[str, int]:
    """Create a short-lived signed access token for a user id."""

    expires_in = get_access_token_expire_minutes() * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "typ": "access",
    }
    token = jwt.encode(payload, get_jwt_secret_key(), algorithm=get_jwt_algorithm())
    return token, expires_in


def decode_access_token(token: str) -> int:
    """Decode and validate an access token, returning its user id."""

    payload = jwt.decode(
        token,
        get_jwt_secret_key(),
        algorithms=[get_jwt_algorithm()],
        options={"require": ["exp", "iat", "sub", "typ"]},
    )
    if payload.get("typ") != "access":
        raise InvalidTokenError("Unsupported token type.")
    subject = payload.get("sub")
    try:
        user_id = int(subject)
    except (TypeError, ValueError) as error:
        raise InvalidTokenError("Invalid token subject.") from error
    if user_id <= 0:
        raise InvalidTokenError("Invalid token subject.")
    return user_id
