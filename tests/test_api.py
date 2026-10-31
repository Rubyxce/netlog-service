from fastapi.testclient import TestClient
import main
import pytest

API_KEY = "test-key"

# 带 key 的客户端：正常业务测试都用它
client = TestClient(main.app, headers={"X-Api-Key": API_KEY})

# 不带 key 的客户端：专门测 401
anon = TestClient(main.app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_logs():
    response = client.get("/logs")
    assert response.status_code == 200


def test_logs_limit():
    response = client.get("/logs?n=abc")
    assert response.status_code == 422


@pytest.mark.parametrize("url,expected", [
    ("/logs", 200),
    ("/logs?n=1", 200),
    ("/logs?n=0", 422),
    ("/logs?n=-1", 422),
])
def test_logs_boundary(url, expected):
    assert client.get(url).status_code == expected


def test_missing_api_key():
    """不带 key → 401"""
    assert anon.get("/logs").status_code == 401


def test_wrong_api_key():
    """带错的 key → 401"""
    bad = TestClient(main.app, headers={"X-Api-Key": "wrong"})
    assert bad.get("/logs").status_code == 401


def test_health_public():
    """探活接口不需要 key"""
    assert anon.get("/health").status_code == 200
