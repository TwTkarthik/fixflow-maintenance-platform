from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check_returns_expected_response() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "fixflow-api"}


def test_cors_allows_configured_frontend_and_rejects_other_origins() -> None:
    allowed = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in allowed.headers["access-control-allow-methods"]

    rejected = client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://unexpected.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
