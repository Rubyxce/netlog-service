from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_logs():
    response = client.get("/logs")
    assert response.status_code == 200


def test_logs_limit():
    response = client.get("/logs?n=abc")
    assert response.status_code == 422
