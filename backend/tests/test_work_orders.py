"""PostgreSQL-backed work-order and maintenance workflow tests."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import MaintenanceRecord, UserRole, WorkOrder, WorkOrderStatus
from tests.test_auth import create_user


def headers_for(db_session: Session, *, email: str, role: UserRole) -> dict[str, str]:
    user = create_user(db_session, email=email, role=role)
    token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def create_asset(client: TestClient, db_session: Session, *, email: str = "asset-owner@example.test") -> dict:
    headers = headers_for(db_session, email=email, role=UserRole.MANAGER)
    response = client.post(
        "/api/assets",
        json={
            "asset_code": f"HVAC-{email.split('@')[0]}",
            "name": "Main HVAC Unit",
            "category": "HVAC",
            "location": "Roof",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def create_work_order(
    client: TestClient,
    headers: dict[str, str],
    asset_id: int,
    **overrides: object,
) -> dict:
    payload = {
        "asset_id": asset_id,
        "title": "Cooling failure",
        "description": "The main unit is not cooling the building.",
        "priority": "high",
        **overrides,
    }
    response = client.post("/api/work-orders", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_manager_can_create_work_order_with_initial_history(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = headers_for(
        db_session, email="create-manager@example.test", role=UserRole.MANAGER
    )
    asset = create_asset(client, db_session, email="create-asset@example.test")

    response = client.post(
        "/api/work-orders",
        json={
            "asset_id": asset["id"],
            "title": "Cooling failure",
            "description": "The main unit is not cooling the building.",
            "priority": "critical",
            "due_at": "2030-01-02T10:00:00Z",
        },
        headers=manager_headers,
    )

    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "open"
    assert created["assigned_to"] is None
    assert created["created_by"]["email"] == "create-manager@example.test"
    history = client.get(f"/api/work-orders/{created['id']}/history", headers=manager_headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["to_status"] == "open"
    assert history.json()[0]["update_type"] == "status_change"


def test_work_order_creation_permissions_and_asset_rules(
    client: TestClient, db_session: Session
) -> None:
    asset = create_asset(client, db_session, email="permission-asset@example.test")
    technician_headers = headers_for(
        db_session, email="create-technician@example.test", role=UserRole.TECHNICIAN
    )
    payload = {
        "asset_id": asset["id"],
        "title": "Broken pump",
        "description": "The pump is leaking.",
        "priority": "medium",
    }
    assert client.post("/api/work-orders", json=payload).status_code == 401
    assert client.post("/api/work-orders", json=payload, headers=technician_headers).status_code == 403
    assert client.post(
        "/api/work-orders",
        json={**payload, "priority": "urgent"},
        headers=technician_headers,
    ).status_code == 403

    manager_headers = headers_for(
        db_session, email="inactive-asset-manager@example.test", role=UserRole.MANAGER
    )
    assert client.post(
        f"/api/assets/{asset['id']}/deactivate", headers=manager_headers
    ).status_code == 200
    response = client.post("/api/work-orders", json=payload, headers=manager_headers)
    assert response.status_code == 409


def test_work_order_list_filters_and_technician_scope(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = headers_for(
        db_session, email="list-manager@example.test", role=UserRole.MANAGER
    )
    technician_one = create_user(
        db_session, email="scope-tech-one@example.test", role=UserRole.TECHNICIAN
    )
    technician_two = create_user(
        db_session, email="scope-tech-two@example.test", role=UserRole.TECHNICIAN
    )
    tech_one_token, _ = create_access_token(technician_one.id)
    tech_two_token, _ = create_access_token(technician_two.id)
    tech_one_headers = {"Authorization": f"Bearer {tech_one_token}"}
    tech_two_headers = {"Authorization": f"Bearer {tech_two_token}"}
    asset = create_asset(client, db_session, email="scope-asset@example.test")

    first = create_work_order(client, manager_headers, asset["id"], title="Motor noise")
    second = create_work_order(client, manager_headers, asset["id"], title="Light failure", priority="low")
    assert client.post(
        f"/api/work-orders/{first['id']}/assign",
        json={"technician_id": technician_one.id},
        headers=manager_headers,
    ).status_code == 200
    assert client.post(
        f"/api/work-orders/{second['id']}/assign",
        json={"technician_id": technician_two.id},
        headers=manager_headers,
    ).status_code == 200

    own = client.get("/api/work-orders", headers=tech_one_headers)
    assert own.status_code == 200
    assert own.json()["total"] == 1
    assert own.json()["items"][0]["id"] == first["id"]
    assert client.get(f"/api/work-orders/{second['id']}", headers=tech_one_headers).status_code == 404
    assert client.get(f"/api/work-orders/{first['id']}", headers=tech_two_headers).status_code == 404

    filtered = client.get(
        "/api/work-orders?priority=low&search=light&skip=0&limit=1",
        headers=manager_headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == second["id"]


def test_assignment_validation_reassignment_and_history(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = headers_for(
        db_session, email="assignment-manager@example.test", role=UserRole.MANAGER
    )
    technician = create_user(
        db_session, email="assignment-tech@example.test", role=UserRole.TECHNICIAN
    )
    second_technician = create_user(
        db_session, email="assignment-tech-two@example.test", role=UserRole.TECHNICIAN
    )
    manager = create_user(
        db_session, email="assignment-other-manager@example.test", role=UserRole.MANAGER
    )
    asset = create_asset(client, db_session, email="assignment-asset@example.test")
    work_order = create_work_order(client, manager_headers, asset["id"])

    invalid = client.post(
        f"/api/work-orders/{work_order['id']}/assign",
        json={"technician_id": manager.id},
        headers=manager_headers,
    )
    assert invalid.status_code == 422
    assigned = client.post(
        f"/api/work-orders/{work_order['id']}/assign",
        json={"technician_id": technician.id},
        headers=manager_headers,
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "assigned"

    repeated = client.post(
        f"/api/work-orders/{work_order['id']}/assign",
        json={"technician_id": technician.id},
        headers=manager_headers,
    )
    assert repeated.status_code == 200
    history = client.get(f"/api/work-orders/{work_order['id']}/history", headers=manager_headers)
    assert len(history.json()) == 2

    reassigned = client.post(
        f"/api/work-orders/{work_order['id']}/assign",
        json={"technician_id": second_technician.id},
        headers=manager_headers,
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["assigned_to"]["id"] == second_technician.id
    assert reassigned.json()["status"] == "assigned"
    final_history = client.get(f"/api/work-orders/{work_order['id']}/history", headers=manager_headers)
    assert final_history.json()[-1]["update_type"] == "assignment"
    assert "Reassigned" in final_history.json()[-1]["note"]


def test_patch_only_updates_metadata_and_rejects_protected_fields(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = headers_for(
        db_session, email="patch-manager@example.test", role=UserRole.MANAGER
    )
    asset = create_asset(client, db_session, email="patch-asset@example.test")
    work_order = create_work_order(client, manager_headers, asset["id"])

    updated = client.patch(
        f"/api/work-orders/{work_order['id']}",
        json={"title": "Updated title", "due_at": None},
        headers=manager_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated title"
    assert updated.json()["status"] == "open"
    assert client.patch(
        f"/api/work-orders/{work_order['id']}",
        json={"status": "completed"},
        headers=manager_headers,
    ).status_code == 422
    assert client.patch(
        f"/api/work-orders/{work_order['id']}",
        json={},
        headers=manager_headers,
    ).status_code == 422


def test_status_rules_notes_completion_and_maintenance_history(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = headers_for(
        db_session, email="workflow-manager@example.test", role=UserRole.MANAGER
    )
    technician = create_user(
        db_session, email="workflow-tech@example.test", role=UserRole.TECHNICIAN
    )
    tech_token, _ = create_access_token(technician.id)
    technician_headers = {"Authorization": f"Bearer {tech_token}"}
    asset = create_asset(client, db_session, email="workflow-asset@example.test")
    work_order = create_work_order(client, manager_headers, asset["id"])

    invalid_completion = client.post(
        f"/api/work-orders/{work_order['id']}/status",
        json={"status": "completed", "completion_summary": "Done"},
        headers=manager_headers,
    )
    assert invalid_completion.status_code == 409
    assert db_session.scalar(select(WorkOrder).where(WorkOrder.id == work_order["id"])).status == WorkOrderStatus.OPEN

    assert client.post(
        f"/api/work-orders/{work_order['id']}/assign",
        json={"technician_id": technician.id},
        headers=manager_headers,
    ).status_code == 200
    assert client.post(
        f"/api/work-orders/{work_order['id']}/status",
        json={"status": "in_progress"},
        headers=technician_headers,
    ).status_code == 200
    note = client.post(
        f"/api/work-orders/{work_order['id']}/notes",
        json={"note": "Inspected the compressor and isolated the fault."},
        headers=technician_headers,
    )
    assert note.status_code == 201
    assert note.json()["update_type"] == "note"
    assert client.post(
        f"/api/work-orders/{work_order['id']}/notes",
        json={"note": "   "},
        headers=technician_headers,
    ).status_code == 422

    completed = client.post(
        f"/api/work-orders/{work_order['id']}/status",
        json={
            "status": "completed",
            "completion_summary": "Cooling restored.",
            "work_performed": "Replaced the failed compressor relay.",
        },
        headers=technician_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None
    record = db_session.scalar(
        select(MaintenanceRecord).where(MaintenanceRecord.work_order_id == work_order["id"])
    )
    assert record is not None
    assert record.performed_by_id == technician.id
    assert record.outcome == "Cooling restored."

    repeated = client.post(
        f"/api/work-orders/{work_order['id']}/status",
        json={"status": "completed", "completion_summary": "Again"},
        headers=technician_headers,
    )
    assert repeated.status_code == 409
    assert db_session.scalar(
        select(func.count(MaintenanceRecord.id)).where(
            MaintenanceRecord.work_order_id == work_order["id"]
        )
    ) == 1

    history = client.get(f"/api/work-orders/{work_order['id']}/history", headers=manager_headers)
    assert history.status_code == 200
    assert [item["update_type"] for item in history.json()] == [
        "status_change",
        "assignment",
        "status_change",
        "note",
        "status_change",
    ]
    maintenance = client.get(
        f"/api/assets/{asset['id']}/maintenance-history", headers=manager_headers
    )
    assert maintenance.status_code == 200
    assert maintenance.json()[0]["work_order_id"] == work_order["id"]
    assert client.get(
        f"/api/work-orders/{work_order['id']}/maintenance", headers=technician_headers
    ).status_code == 200


def test_terminal_records_and_unrelated_maintenance_are_scoped(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = headers_for(
        db_session, email="terminal-manager@example.test", role=UserRole.MANAGER
    )
    technician = create_user(
        db_session, email="terminal-tech@example.test", role=UserRole.TECHNICIAN
    )
    other_technician = create_user(
        db_session, email="terminal-other-tech@example.test", role=UserRole.TECHNICIAN
    )
    tech_token, _ = create_access_token(technician.id)
    other_token, _ = create_access_token(other_technician.id)
    technician_headers = {"Authorization": f"Bearer {tech_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}
    asset = create_asset(client, db_session, email="terminal-asset@example.test")
    work_order = create_work_order(client, manager_headers, asset["id"])
    assert client.post(
        f"/api/work-orders/{work_order['id']}/assign",
        json={"technician_id": technician.id},
        headers=manager_headers,
    ).status_code == 200
    assert client.post(
        f"/api/work-orders/{work_order['id']}/status",
        json={"status": "in_progress"},
        headers=technician_headers,
    ).status_code == 200
    assert client.post(
        f"/api/work-orders/{work_order['id']}/status",
        json={"status": "completed", "note": "Completed successfully."},
        headers=technician_headers,
    ).status_code == 200
    assert client.post(
        f"/api/work-orders/{work_order['id']}/notes",
        json={"note": "Post-completion note"},
        headers=technician_headers,
    ).status_code == 409
    assert client.get(
        f"/api/assets/{asset['id']}/maintenance-history", headers=other_headers
    ).json() == []

