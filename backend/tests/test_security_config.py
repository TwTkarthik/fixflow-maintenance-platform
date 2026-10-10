import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import (
    get_access_token_expire_minutes,
    get_app_environment,
    get_jwt_algorithm,
    get_jwt_secret_key,
    validate_runtime_configuration,
)


def test_jwt_configuration_rejects_unsafe_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIXFLOW_ENVIRONMENT", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "short")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        get_jwt_secret_key()

    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
    monkeypatch.setenv("JWT_ALGORITHM", "HS384")
    with pytest.raises(RuntimeError, match="must be HS256"):
        get_jwt_algorithm()

    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "0")
    with pytest.raises(RuntimeError, match="positive integer"):
        get_access_token_expire_minutes()

    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "not-a-number")
    with pytest.raises(RuntimeError, match="positive integer"):
        get_access_token_expire_minutes()


def test_production_rejects_the_documented_jwt_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIXFLOW_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "JWT_SECRET_KEY", "replace-with-a-random-secret-at-least-32-characters"
    )

    with pytest.raises(RuntimeError, match="cryptographically random"):
        validate_runtime_configuration()


def test_production_rejects_insufficient_secret_strength(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIXFLOW_ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 64)

    with pytest.raises(RuntimeError, match="at least 32 bytes of entropy"):
        get_jwt_secret_key()


def test_production_rejects_the_repeated_human_phrase_found_in_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIXFLOW_ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "thisisasecret1234" * 4)

    with pytest.raises(RuntimeError, match="at least 32 bytes of entropy"):
        get_jwt_secret_key()


def test_production_accepts_random_urlsafe_and_hex_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIXFLOW_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://fixflow@db:5432/fixflow_dev"
    )
    monkeypatch.delenv("PGPASSWORD", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    for secret in (secrets.token_urlsafe(32), secrets.token_hex(32)):
        monkeypatch.setenv("JWT_SECRET_KEY", secret)
        validate_runtime_configuration()


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://fixflow:replace-with-local-password@db:5432/fixflow_dev",
        "postgresql+psycopg://fixflow:replace%2Dwith%2Dlocal%2Dpassword@db:5432/fixflow_dev",
    ],
)
def test_production_rejects_the_documented_database_password_placeholder(
    monkeypatch: pytest.MonkeyPatch, database_url: str
) -> None:
    monkeypatch.setenv("FIXFLOW_ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    monkeypatch.delenv("PGPASSWORD", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(RuntimeError, match="database configuration") as error:
        validate_runtime_configuration()
    assert "replace" not in str(error.value).lower()


def test_production_rejects_a_malformed_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIXFLOW_ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    monkeypatch.setenv("DATABASE_URL", "not-a-postgresql-url")

    with pytest.raises(RuntimeError, match="valid PostgreSQL"):
        validate_runtime_configuration()


def _run_production_app_import(secret: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "FIXFLOW_ENVIRONMENT": "production",
            "JWT_SECRET_KEY": secret,
            "DATABASE_URL": "postgresql+psycopg://fixflow@db:5432/fixflow_dev",
        }
    )
    environment.pop("PGPASSWORD", None)
    environment.pop("POSTGRES_PASSWORD", None)
    return subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_validation_runs_during_app_import() -> None:
    valid_result = _run_production_app_import(secrets.token_urlsafe(32))
    assert valid_result.returncode == 0

    placeholder_result = _run_production_app_import(
        "replace-with-a-random-secret-at-least-32-characters"
    )
    assert placeholder_result.returncode != 0
    assert "JWT_SECRET_KEY" in placeholder_result.stderr


def test_development_default_preserves_existing_secret_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FIXFLOW_ENVIRONMENT", raising=False)
    placeholder = "replace-with-a-random-secret-at-least-32-characters"
    monkeypatch.setenv("JWT_SECRET_KEY", placeholder)

    assert get_app_environment() == "development"
    assert get_jwt_secret_key() == placeholder
