from fastapi.testclient import TestClient
import main
import pytest

API_KEY = "test-key"

# 设备上报用：X-Api-Key
client = TestClient(main.app, headers={"X-Api-Key": API_KEY})

# 完全匿名
anon = TestClient(main.app)


@pytest.fixture(scope="module")
def auth():
    """注册一个测试用户并登录，返回带 Bearer 的客户端。

    用户名固定，重复跑测试时 register 会返回 400（已存在），忽略即可。
    """
    username, password = "test_user", "test123456"

    anon.post("/auth/register", json={"username": username, "password": password})

    r = anon.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text

    token = r.json()["access_token"]
    return TestClient(main.app, headers={"Authorization": f"Bearer {token}"})


def test_health():
    assert anon.get("/health").status_code == 200


def test_logs(auth):
    assert auth.get("/logs").status_code == 200


def test_logs_limit(auth):
    assert auth.get("/logs?n=abc").status_code == 422


@pytest.mark.parametrize("url,expected", [
    ("/logs", 200),
    ("/logs?n=1", 200),
    ("/logs?n=0", 422),
    ("/logs?n=-1", 422),
])
def test_logs_boundary(auth, url, expected):
    assert auth.get(url).status_code == expected


# ---------- 鉴权测试 ----------

def test_missing_token():
    """不带 token → 401"""
    assert anon.get("/logs").status_code == 401


def test_wrong_token():
    """伪造的 token（签名不对）→ 401"""
    bad = TestClient(main.app, headers={"Authorization": "Bearer abc.def.ghi"})
    assert bad.get("/logs").status_code == 401


def test_bad_scheme():
    """少了 Bearer 前缀 → 401"""
    bad = TestClient(main.app, headers={"Authorization": "abc.def.ghi"})
    assert bad.get("/logs").status_code == 401


def test_post_logs_requires_api_key():
    """上报接口仍然要 API Key（设备不会登录）"""
    assert anon.post("/logs", json=[]).status_code == 401


def test_post_logs_rejects_token_only(auth):
    """只带 JWT、没有 API Key，上报接口要拒绝"""
    assert auth.post("/logs", json=[]).status_code == 401


def test_stats(auth):
    assert auth.get("/stats").status_code == 200


def test_stats_requires_token():
    assert anon.get("/stats").status_code == 401


# ---------- 公开接口 ----------

def test_health_public():
    """探活接口不需要鉴权"""
    assert anon.get("/health").status_code == 200


def test_index_page():
    """根路径返回页面骨架，不需要鉴权（页面里没有数据）"""
    response = anon.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_static_asset():
    """静态资源能按 /static/... 取到"""
    assert anon.get("/static/vendor/echarts.min.js").status_code == 200


# ---------- 排序 ----------

def test_logs_order_desc(auth):
    """order=desc 时最新的排在最前（id 从大到小）"""
    rows = auth.get("/logs?n=5&order=desc").json()["data"]
    ids = [r["id"] for r in rows]
    assert ids == sorted(ids, reverse=True)


def test_logs_order_invalid(auth):
    """order 只接受 asc / desc，其他值 422"""
    assert auth.get("/logs?order=xxx").status_code == 422


# ---------- 注册 / 登录 ----------

def test_register_duplicate():
    """同一个用户名注册两次 → 400"""
    anon.post("/auth/register", json={"username": "dup_user", "password": "123456"})
    r = anon.post("/auth/register", json={"username": "dup_user", "password": "123456"})
    assert r.status_code == 400


def test_login_wrong_password():
    """密码错 → 401"""
    anon.post("/auth/register", json={"username": "pw_user", "password": "correct123"})
    r = anon.post("/auth/login", json={"username": "pw_user", "password": "wrong"})
    assert r.status_code == 401


def test_register_short_password():
    """密码太短 → 400"""
    r = anon.post("/auth/register", json={"username": "short_pw", "password": "123"})
    assert r.status_code == 400
