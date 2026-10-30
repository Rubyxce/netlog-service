# netlog-service

基于 FastAPI + SQLite 的网络日志查询服务。

## 技术栈
fastapi / uvicorn / sqlite3 / pytest / httpx

## 快速开始

# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成数据（首次必须做，logs.db 不进 Git）
python seed.py

# 3. 启动服务（必须在项目根目录下执行）
uvicorn main:app --reload

打开 http://127.0.0.1:8000/docs

## 接口列表
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /health | 健康检查 |
| GET | /logs | 查询日志，支持 device / level / n / page |
| GET | /logs/{log_id} | 按 id 查单条 |
| GET | /stats | 按级别、按设备统计 |
| POST | /logs | 批量上报日志 |