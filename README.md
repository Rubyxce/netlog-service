# netlog-service

基于 FastAPI + SQLite 的网络日志查询服务。

## 技术栈
fastapi / uvicorn / sqlite3 / pytest / httpx

## 快速开始

```
# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成数据（首次必须做，logs.db 不进 Git）
python seed.py

# 3. 设置 API Key（必须，否则受保护接口返回 500）
$env:API_KEY = "your-secret-key"        # PowerShell
# export API_KEY="your-secret-key"      # Linux / macOS

# 4. 启动服务（必须在项目根目录下执行）
uvicorn main:app --reload
```

打开 http://127.0.0.1:8000/docs

## 接口列表

| 方法 | 路径 | 说明 | 需要 API Key |
|---|---|---|---|
| GET | /health | 健康检查 | ❌ |
| GET | /logs | 查询日志，支持 device / level / n / page | ✅ |
| GET | /logs/{log_id} | 按 id 查单条 | ✅ |
| GET | /stats | 按级别、按设备统计 | ✅ |
| POST | /logs | 批量上报日志 | ✅ |

## 鉴权

受保护的接口要在请求头里带 `X-Api-Key`：

```
curl -H "X-Api-Key: your-secret-key" http://127.0.0.1:8000/logs
```

| 情况 | 返回 |
|---|---|
| 不带 key、或 key 不对 | `401 {"detail": "invalid api key"}` |
| 服务端没配 `API_KEY` 环境变量 | `500 {"detail": "server not configured"}` |
| `/health` | 不鉴权，供负载均衡探活 |

密钥从环境变量读，**不要写进代码、不要提交到仓库**。

## 测试

```
pytest -q
```

`conftest.py` 会设置测试用的 `API_KEY=test-key`，不影响你的开发环境。
