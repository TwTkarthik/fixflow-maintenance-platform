"""PostgreSQL-backed equipment API tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import User, UserRole
from tests.test_auth import PASSWORD, create_user


def auth_headers(db_session: Session, *, email: str, role: UserRole) -> dict[str, str]:
    user = create_user(db_session, email=email, role=role)
    token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def asset_payload(
    *,
    asset_code: str = "HVAC-001",
    name: str = "Main HVAC Unit",
    category: str = "HVAC",
    location: str = "Roof",
) -> dict[str, str]:
    return {
        "asset_code": asset_code,
        "name": name,
        "category": category,
        "location": location,
        "serial_number": "SN-001",
        "manufacturer": "FixFlow Systems",
        "model": "X100",
        "description": "Primary building climate unit.",
    }


def create_asset(
    client: TestClient,
    db_session: Session,
    *,
    role: UserRole = UserRole.MANAGER,
    email: str = "manager-assets@example.test",
    **overrides: str,
) -> dict:
    response = client.post(
        "/api/assets",
        json={**asset_payload(**overrides), **overrides},
        headers=auth_headers(db_session, email=email, role=role),
    )
    assert response.status_code == 201
    return response.json()


def test_all_authenticated_roles_can_list_and_retrieve_assets(
    client: TestClient, db_session: Session
) -> None:
    created = create_asset(client, db_session)

    for role, email in [
        (UserRole.ADMINISTRATOR, "admin-list@example.test"),
        (UserRole.MANAGER, "manager-list@example.test"),
        (UserRole.TECHNICIAN, "tech-list@example.test"),
    ]:
        headers = auth_headers(db_session, email=email, role=role)
        listed = client.get("/api/assets", headers=headers)
        retrieved = client.get(f"/api/assets/{created['id']}", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["items"][0]["asset_code"] == "HVAC-001"
        assert retrieved.status_code == 200
        assert retrieved.json()["id"] == created["id"]


def test_unauthenticated_listing_and_missing_asset_are_rejected(
    client: TestClient, db_session: Session
) -> None:
    assert client.get("/api/assets").status_code == 401
    headers = auth_headers(
        db_session, email="missing-asset@example.test", role=UserRole.TECHNICIAN
    )
    assert client.get("/api/assets/999999", headers=headers).status_code == 404


def test_listing_search_filters_status_and_pagination(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(
        db_session, email="filter-assets@example.test", role=UserRole.MANAGER
    )
    for payload in [
        asset_payload(asset_code="PUMP-001", name="North Water Pump", category="Pumps", location="North"),
        asset_payload(asset_code="PUMP-002", name="South Water Pump", category="Pumps", location="South"),
        asset_payload(asset_code="GEN-001", name="Backup Generator", category="Power", location="South"),
    ]:
        assert client.post("/api/assets", json=payload, headers=headers).status_code == 201

    search = client.get("/api/assets?search=water", headers=headers)
    category = client.get("/api/assets?category=Pumps&location=South", headers=headers)
    page = client.get("/api/assets?skip=1&limit=1", headers=headers)
    assert [item["asset_code"] for item in search.json()["items"]] == ["PUMP-001", "PUMP-002"]
    assert [item["asset_code"] for item in category.json()["items"]] == ["PUMP-002"]
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 1
    assert page.json()["items"][0]["asset_code"] == "PUMP-002"

    asset_id = page.json()["items"][0]["id"]
    assert client.post(f"/api/assets/{asset_id}/deactivate", headers=headers).status_code == 200
    inactive = client.get("/api/assets?status=deactivated", headers=headers)
    active = client.get("/api/assets?status=active", headers=headers)
    assert [item["id"] for item in inactive.json()["items"]] == [asset_id]
    assert all(item["id"] != asset_id for item in active.json()["items"])


def test_invalid_pagination_and_validation_are_rejected(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(
        db_session, email="validation-assets@example.test", role=UserRole.MANAGER
    )
    assert client.get("/api/assets?limit=101", headers=headers).status_code == 422
    assert client.post(
        "/api/assets",
        json={**asset_payload(), "name": "   "},
        headers=headers,
    ).status_code == 422
    created = client.post("/api/assets", json=asset_payload(), headers=headers).json()
    assert client.patch(
        f"/api/assets/{created['id']}", json={}, headers=headers
    ).status_code == 422


def test_managers_and_administrators_can_create_update_and_deactivate(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = auth_headers(
        db_session, email="manager-write@example.test", role=UserRole.MANAGER
    )
    created_response = client.post(
        "/api/assets", json=asset_payload(), headers=manager_headers
    )
    assert created_response.status_code == 201
    created = created_response.json()

    updated = client.patch(
        f"/api/assets/{created['id']}",
        json={"location": "Basement", "description": None},
        headers=manager_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["location"] == "Basement"
    assert updated.json()["name"] == "Main HVAC Unit"
    assert updated.json()["description"] is None

    deactivated = client.post(
        f"/api/assets/{created['id']}/deactivate", headers=manager_headers
    )
    repeated = client.post(
        f"/api/assets/{created['id']}/deactivate", headers=manager_headers
    )
    retrieved = client.get(
        f"/api/assets/{created['id']}", headers=manager_headers
    )
    assert deactivated.status_code == 200
    assert repeated.status_code == 200
    assert retrieved.json()["status"] == "deactivated"


def test_technicians_are_read_only_and_unauthenticated_writes_fail(
    client: TestClient, db_session: Session
) -> None:
    technician_headers = auth_headers(
        db_session, email="tech-write@example.test", role=UserRole.TECHNICIAN
    )
    for method, path in [
        ("post", "/api/assets"),
        ("patch", "/api/assets/1"),
        ("post", "/api/assets/1/deactivate"),
    ]:
        response = getattr(client, method)(
            path,
            json=asset_payload() if method != "post" or path == "/api/assets" else None,
            headers=technician_headers,
        )
        assert response.status_code in {403, 404}
    assert client.post("/api/assets", json=asset_payload()).status_code == 401


def test_duplicate_codes_return_conflict_without_internal_details(
    client: TestClient, db_session: Session
) -> None:
    headers = auth_headers(
        db_session, email="duplicate-assets@example.test", role=UserRole.ADMINISTRATOR
    )
    assert client.post("/api/assets", json=asset_payload(), headers=headers).status_code == 201
    duplicate = client.post("/api/assets", json=asset_payload(name="Other"), headers=headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "An asset with that asset code already exists."
    assert "sql" not in duplicate.text.lower()
    assert "traceback" not in duplicate.text.lower()
