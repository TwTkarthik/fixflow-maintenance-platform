"""Authentication, token validation, and role authorization tests."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.config import get_jwt_algorithm, get_jwt_secret_key
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models import User, UserRole


PASSWORD = "correct horse battery staple"


def create_user(
    db_session: Session,
    *,
    email: str = "manager@example.test",
    role: UserRole = UserRole.MANAGER,
    is_active: bool = True,
) -> User:
    user = User(
        full_name="Test User",
        email=email,
        password_hash=hash_password(PASSWORD),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_password_hashing_never_matches_plaintext() -> None:
    password_hash = hash_password(PASSWORD)

    assert password_hash != PASSWORD
    assert verify_password(PASSWORD, password_hash)
    assert not verify_password("wrong password", password_hash)


def test_valid_credentials_login_and_access_me(
    client: TestClient, db_session: Session
) -> None:
    create_user(db_session)

    login_response = client.post(
        "/api/auth/login",
        json={"email": "MANAGER@example.test", "password": PASSWORD},
    )

    assert login_response.status_code == 200
    token_response = login_response.json()
    assert token_response["token_type"] == "bearer"
    assert token_response["expires_in"] > 0
    assert "access_token" in token_response

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_response['access_token']}"},
    )

    assert me_response.status_code == 200
    profile = me_response.json()
    assert profile["email"] == "manager@example.test"
    assert profile["role"] == "manager"
    assert profile["is_active"] is True
    assert "password_hash" not in profile


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("manager@example.test", "wrong password"),
        ("missing@example.test", PASSWORD),
    ],
)
def test_invalid_credentials_use_one_generic_response(
    client: TestClient, db_session: Session, email: str, password: str
) -> None:
    create_user(db_session)

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."
    assert response.headers["www-authenticate"] == "Bearer"


def test_disabled_accounts_cannot_login(
    client: TestClient, db_session: Session
) -> None:
    create_user(db_session, is_active=False)

    response = client.post(
        "/api/auth/login",
        json={"email": "manager@example.test", "password": PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_missing_malformed_expired_and_bad_signature_tokens_are_rejected(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session)
    valid_token, _ = create_access_token(user.id)

    responses = [
        client.get("/api/auth/me"),
        client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"}),
        client.get(
            "/api/auth/me",
            headers={
                "Authorization": "Bearer "
                + jwt.encode(
                    {
                        "sub": str(user.id),
                        "iat": datetime.now(UTC) - timedelta(hours=2),
                        "exp": datetime.now(UTC) - timedelta(hours=1),
                        "typ": "access",
                    },
                    get_jwt_secret_key(),
                    algorithm=get_jwt_algorithm(),
                )
            },
        ),
        client.get(
            "/api/auth/me",
            headers={
                "Authorization": "Bearer "
                + jwt.encode(
                    jwt.decode(
                        valid_token,
                        get_jwt_secret_key(),
                        algorithms=[get_jwt_algorithm()],
                    ),
                    get_jwt_secret_key(),
                    algorithm="HS384",
                )
            },
        ),
        client.get(
            "/api/auth/me",
            headers={
                "Authorization": "Bearer "
                + jwt.encode(
                    jwt.decode(
                        valid_token,
                        get_jwt_secret_key(),
                        algorithms=[get_jwt_algorithm()],
                    ),
                    "wrong-signing-key",
                    algorithm=get_jwt_algorithm(),
                )
            },
        ),
    ]

    assert all(response.status_code == 401 for response in responses)
    assert all(
        response.headers["www-authenticate"] == "Bearer" for response in responses
    )


def test_deleted_or_deactivated_users_cannot_use_old_tokens(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session)
    token, _ = create_access_token(user.id)
    db_session.delete(user)
    db_session.flush()

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_role_dependency_allows_and_denies_roles() -> None:
    permitted_user = User(role=UserRole.MANAGER)
    forbidden_user = User(role=UserRole.TECHNICIAN)
    manager_only = require_roles(UserRole.ADMINISTRATOR, UserRole.MANAGER)

    assert manager_only(permitted_user) is permitted_user
    with pytest.raises(HTTPException) as error:
        manager_only(forbidden_user)
    assert error.value.status_code == 403
