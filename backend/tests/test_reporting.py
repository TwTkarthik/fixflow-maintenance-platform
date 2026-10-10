"""PostgreSQL-backed dashboard and reporting tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import UserRole
from tests.test_auth import create_user
from tests.test_work_orders import create_asset, create_work_order, headers_for


def test_empty_dashboard_is_zero_safe(client: TestClient, db_session: Session) -> None:
    headers = headers_for(db_session, email="empty-dashboard@example.test", role=UserRole.MANAGER)

    response = client.get("/api/dashboard", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_assets"] == 0
    assert payload["total_work_orders"] == 0
    assert payload["outstanding_work_orders"] == 0
    assert payload["overdue_work_orders"] == 0
    assert payload["total_maintenance_records"] == 0
    assert all(item["count"] == 0 for item in payload["status_counts"])
    assert all(item["count"] == 0 for item in payload["priority_counts"])


def test_dashboard_aggregates_real_records_and_date_filter(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = headers_for(
        db_session, email="dashboard-manager@example.test", role=UserRole.MANAGER
    )
    technician = create_user(
        db_session, email="dashboard-tech@example.test", role=UserRole.TECHNICIAN
    )
    tech_token, _ = create_access_token(technician.id)
    technician_headers = {"Authorization": f"Bearer {tech_token}"}
    asset = create_asset(client, db_session, email="dashboard-asset@example.test")

    overdue_open = create_work_order(
        client,
        manager_headers,
        asset["id"],
        title="Overdue open repair",
        due_at="2020-01-01T00:00:00Z",
    )
    assigned = create_work_order(
        client,
        manager_headers,
        asset["id"],
        title="Assigned repair",
        priority="critical",
        due_at="2030-01-01T00:00:00Z",
    )
    completed = create_work_order(
        client,
        manager_headers,
        asset["id"],
        title="Completed repair",
        priority="low",
        due_at="2030-01-02T00:00:00Z",
    )
    assert client.post(
        f"/api/work-orders/{assigned['id']}/assign",
        json={"technician_id": technician.id},
        headers=manager_headers,
    ).status_code == 200
    assert client.post(
        f"/api/work-orders/{completed['id']}/assign",
        json={"technician_id": technician.id},
        headers=manager_headers,
    ).status_code == 200
    assert client.post(
        f"/api/work-orders/{completed['id']}/status",
        json={"status": "in_progress"},
        headers=technician_headers,
    ).status_code == 200
    assert client.post(
        f"/api/work-orders/{completed['id']}/status",
        json={"status": "completed", "completion_summary": "Repair completed."},
        headers=technician_headers,
    ).status_code == 200

    response = client.get("/api/dashboard", headers=manager_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_assets"] == 1
    assert payload["active_assets"] == 1
    assert payload["total_work_orders"] == 3
    assert payload["outstanding_work_orders"] == 2
    assert payload["overdue_work_orders"] == 1
    assert payload["completed_work_orders"] == 1
    assert payload["total_maintenance_records"] == 1
    assert payload["assets_needing_attention"] == 1
    status_counts = {item["value"]: item["count"] for item in payload["status_counts"]}
    assert status_counts == {
        "open": 1,
        "assigned": 1,
        "in_progress": 0,
        "on_hold": 0,
        "completed": 1,
        "cancelled": 0,
    }

    filtered = client.get(
        "/api/dashboard?date_from=2026-01-01&date_to=2026-12-31",
        headers=manager_headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["total_work_orders"] == 3
    assert filtered.json()["total_maintenance_records"] == 1
    assert overdue_open["id"] != completed["id"]


def test_work_order_report_combines_filters_and_paginates(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = headers_for(
        db_session, email="work-report-manager@example.test", role=UserRole.MANAGER
    )
    asset = create_asset(client, db_session, email="work-report-asset@example.test")
    create_work_order(
        client,
        manager_headers,
        asset["id"],
        title="North pump repair",
        priority="high",
        due_at="2030-01-01T00:00:00Z",
    )
    matching = create_work_order(
        client,
        manager_headers,
        asset["id"],
        title="South pump repair",
        priority="high",
        due_at="2030-01-01T00:00:00Z",
    )
    create_work_order(
        client,
        manager_headers,
        asset["id"],
        title="South lighting repair",
        priority="low",
        due_at="2030-01-01T00:00:00Z",
    )

    response = client.get(
        "/api/reports/work-orders?date_from=2026-01-01&date_to=2026-12-31"
        "&priority=high&search=South&skip=0&limit=1",
        headers=manager_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == matching["id"]
    assert payload["items"][0]["is_overdue"] is False

    assert client.get(
        "/api/reports/work-orders?date_from=2030-01-02&date_to=2030-01-01",
        headers=manager_headers,
    ).status_code == 422
    assert client.get(
        "/api/reports/work-orders?limit=101", headers=manager_headers
    ).status_code == 422
    assert client.get("/api/reports/work-orders").status_code == 401


def test_reports_and_dashboard_are_isolated_for_technicians(
    client: TestClient, db_session: Session
) -> None:
    manager_headers = headers_for(
        db_session, email="scope-report-manager@example.test", role=UserRole.MANAGER
    )
    technician_one = create_user(
        db_session, email="scope-report-tech-one@example.test", role=UserRole.TECHNICIAN
    )
    technician_two = create_user(
        db_session, email="scope-report-tech-two@example.test", role=UserRole.TECHNICIAN
    )
    token_one, _ = create_access_token(technician_one.id)
    token_two, _ = create_access_token(technician_two.id)
    headers_one = {"Authorization": f"Bearer {token_one}"}
    headers_two = {"Authorization": f"Bearer {token_two}"}
    asset = create_asset(client, db_session, email="scope-report-asset@example.test")

    first = create_work_order(client, manager_headers, asset["id"], title="Tech one repair")
    second = create_work_order(client, manager_headers, asset["id"], title="Tech two repair")
    for work_order, technician_id, technician_headers in [
        (first, technician_one.id, headers_one),
        (second, technician_two.id, headers_two),
    ]:
        assert client.post(
            f"/api/work-orders/{work_order['id']}/assign",
            json={"technician_id": technician_id},
            headers=manager_headers,
        ).status_code == 200
        assert client.post(
            f"/api/work-orders/{work_order['id']}/status",
            json={"status": "in_progress"},
            headers=technician_headers,
        ).status_code == 200
        assert client.post(
            f"/api/work-orders/{work_order['id']}/status",
            json={"status": "completed", "completion_summary": "Completed."},
            headers=technician_headers,
        ).status_code == 200

    dashboard = client.get("/api/dashboard", headers=headers_one)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_work_orders"] == 1
    assert dashboard.json()["total_maintenance_records"] == 1
    assert dashboard.json()["total_assets"] == 1

    work_report = client.get("/api/reports/work-orders", headers=headers_one)
    assert work_report.status_code == 200
    assert work_report.json()["total"] == 1
    assert work_report.json()["items"][0]["id"] == first["id"]
    maintenance_report = client.get(
        "/api/reports/maintenance?status=completed&priority=high&search=Completed",
        headers=headers_one,
    )
    assert maintenance_report.status_code == 200
    assert maintenance_report.json()["total"] == 1
    assert maintenance_report.json()["items"][0]["work_order_id"] == first["id"]

    assert client.get(
        f"/api/reports/work-orders?assigned_to_id={technician_two.id}",
        headers=headers_one,
    ).json()["total"] == 0
    assert client.get(
        f"/api/assets/{asset['id']}/maintenance-history", headers=headers_one
    ).json()[0]["work_order_id"] == first["id"]

