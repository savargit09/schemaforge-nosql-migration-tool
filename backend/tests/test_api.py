from fastapi.testclient import TestClient
from app.main import app


def test_health_and_openapi_available_without_database():
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        spec = client.get("/openapi.json")
        assert spec.status_code == 200
        assert "/api/migrations" in spec.json()["paths"]


def test_migration_validates_input_before_database_call():
    with TestClient(app) as client:
        response = client.post("/api/migrations", json={"ddl":"bad", "queries":[]})
        assert response.status_code == 422
