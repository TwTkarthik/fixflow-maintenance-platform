"""Environment-backed application configuration."""

import os

from dotenv import load_dotenv


load_dotenv()


def get_database_url() -> str:
    """Return the configured PostgreSQL URL or explain how to configure it."""

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Copy backend/.env.example to "
            "backend/.env and set a local PostgreSQL connection URL."
        )
    return database_url


def get_jwt_secret_key() -> str:
    """Return the required local JWT signing secret."""

    secret_key = os.getenv("JWT_SECRET_KEY", "").strip()
    if len(secret_key) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured or is too short. "
            "Set a random secret of at least 32 characters in backend/.env."
        )
    return secret_key


def get_jwt_algorithm() -> str:
    """Return the only supported JWT algorithm."""

    algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
    if algorithm != "HS256":
        raise RuntimeError("JWT_ALGORITHM must be HS256.")
    return algorithm


def get_access_token_expire_minutes() -> int:
    """Return a positive access-token lifetime in minutes."""

    raw_value = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30").strip()
    try:
        minutes = int(raw_value)
    except ValueError as error:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer."
        ) from error
    if minutes <= 0:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer."
        )
    return minutes
