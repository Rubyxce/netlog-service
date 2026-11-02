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

def test_index_page():
    """根路径返回页面骨架，而且不需要 key（页面里没有数据）"""
    response = anon.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_static_asset():
    """静态资源能按 /static/... 取到"""
    assert client.get("/static/vendor/echarts.min.js").status_code == 200


def test_logs_order_desc():
    """order=desc 时最新的排在最前（id 从大到小）"""
    rows = client.get("/logs?n=5&order=desc").json()["data"]
    ids = [r["id"] for r in rows]
    assert ids == sorted(ids, reverse=True)


def test_logs_order_invalid():
    """order 只接受 asc / desc，其他值 422"""
    assert client.get("/logs?order=xxx").status_code == 422
