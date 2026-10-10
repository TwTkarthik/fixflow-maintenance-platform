import pytest

from app.core.config import (
    get_access_token_expire_minutes,
    get_jwt_algorithm,
    get_jwt_secret_key,
)


def test_jwt_configuration_rejects_unsafe_values(monkeypatch: pytest.MonkeyPatch) -> None:
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
