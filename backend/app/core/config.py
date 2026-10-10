"""Environment-backed application configuration."""

import base64
import binascii
import os
import re
from urllib.parse import unquote, urlsplit

from dotenv import load_dotenv


load_dotenv()

_SUPPORTED_ENVIRONMENTS = {"development", "production"}
_KNOWN_JWT_PLACEHOLDERS = {
    "replace-with-a-random-secret-at-least-32-characters",
}
_KNOWN_WEAK_JWT_MARKERS = (
    "password",
    "letmein",
    "changeme",
    "correcthorse",
    "secret",
)
_KNOWN_DATABASE_PASSWORD_PLACEHOLDERS = {
    "replace-with-a-local-only-password",
    "replace-with-local-password",
}


def get_app_environment() -> str:
    """Return the configured application environment."""

    environment = os.getenv("FIXFLOW_ENVIRONMENT", "development").strip().lower()
    if environment not in _SUPPORTED_ENVIRONMENTS:
        raise RuntimeError(
            "FIXFLOW_ENVIRONMENT must be development or production."
        )
    return environment


def _is_known_placeholder(value: str, placeholders: set[str]) -> bool:
    return value.strip().lower() in placeholders


def _decoded_urlsafe_secret(secret: str) -> bytes | None:
    """Decode an unpadded URL-safe base64 secret, if it is canonical."""

    if not re.fullmatch(r"[A-Za-z0-9_-]+", secret):
        return None
    padded = secret + "=" * (-len(secret) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded)
    except (binascii.Error, ValueError):
        return None
    canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    return decoded if canonical == secret else None


def _has_repeated_block(value: str) -> bool:
    """Reject values made entirely from a repeated text block."""

    for block_size in range(1, len(value) // 2 + 1):
        if len(value) % block_size == 0 and value == value[:block_size] * (len(value) // block_size):
            return True
    return False


def _has_32_bytes_of_entropy(secret: str) -> bool:
    """Accept standard encodings and reject obvious weak values.

    A string cannot prove how it was generated, so this only rejects known or
    clearly repetitive values while requiring a 32-byte decoded representation.
    """

    normalized = secret.lower()
    if (
        len(set(secret)) < 8
        or _has_repeated_block(secret)
        or any(marker in normalized for marker in _KNOWN_WEAK_JWT_MARKERS)
    ):
        return False

    decoded = _decoded_urlsafe_secret(secret)
    if decoded is not None and len(decoded) >= 32:
        return len(set(decoded)) >= 8

    if re.fullmatch(r"[0-9a-fA-F]+", secret) and len(secret) % 2 == 0:
        try:
            decoded = bytes.fromhex(secret)
        except ValueError:
            return False
        return len(decoded) >= 32 and len(set(decoded)) >= 8

    return False


def get_database_url() -> str:
    """Return the configured PostgreSQL URL or explain how to configure it."""

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Copy backend/.env.example to "
            "backend/.env and set a local PostgreSQL connection URL."
        )
    return database_url


def _parse_database_url(database_url: str):
    """Parse and validate the configured PostgreSQL URL without exposing it."""

    try:
        parsed_url = urlsplit(database_url)
        if (
            parsed_url.scheme not in {"postgresql", "postgresql+psycopg"}
            or not parsed_url.hostname
            or not parsed_url.path.strip("/")
        ):
            raise ValueError
    except ValueError:
        raise RuntimeError(
            "DATABASE_URL must be a valid PostgreSQL connection URL."
        ) from None
    return parsed_url


def get_jwt_secret_key() -> str:
    """Return the configured JWT signing secret."""

    secret_key = os.getenv("JWT_SECRET_KEY", "").strip()
    if not secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured. Set a random secret in backend/.env."
        )
    if get_app_environment() == "production":
        if _is_known_placeholder(
            secret_key, _KNOWN_JWT_PLACEHOLDERS
        ) or not _has_32_bytes_of_entropy(secret_key):
            raise RuntimeError(
                "Production JWT_SECRET_KEY must be a cryptographically random "
                "URL-safe or hexadecimal secret containing at least 32 bytes of entropy."
            )
    elif len(secret_key) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY is too short. Set a random secret of at least 32 characters in backend/.env."
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


def _configured_database_passwords() -> list[str]:
    """Return configured database passwords without logging their values."""

    passwords = [
        os.getenv("POSTGRES_PASSWORD", ""),
        os.getenv("PGPASSWORD", ""),
    ]
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed_url = _parse_database_url(database_url)
        if parsed_url.password:
            passwords.append(unquote(parsed_url.password))
    return passwords


def validate_runtime_configuration() -> None:
    """Fail fast on production-only configuration hazards."""

    if get_app_environment() != "production":
        return

    get_jwt_secret_key()
    get_jwt_algorithm()
    get_access_token_expire_minutes()
    get_database_url()

    if any(
        _is_known_placeholder(password, _KNOWN_DATABASE_PASSWORD_PLACEHOLDERS)
        for password in _configured_database_passwords()
        if password
    ):
        raise RuntimeError(
            "Production database configuration contains a documented password placeholder."
        )
