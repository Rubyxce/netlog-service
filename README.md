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

## 可视化页面

启动服务后直接打开 <http://127.0.0.1:8000/>：

| 板块 | 数据来源 |
|---|---|
| 总日志数 / ERROR 条数 / 设备数 | `GET /stats` |
| 按级别分布（饼图） | `GET /stats` → `by_level` |
| 按设备分布（柱状图） | `GET /stats` → `by_device` |
| 最近 20 条日志（表格） | `GET /logs?n=20&order=desc` |
| 自动刷新 | 每 5 秒重新拉一次 |

第一次打开要填 API Key（填完回车，存在浏览器 `localStorage`）。

实现上没有构建链：`static/index.html` 一个文件装下 HTML / CSS / JS，
ECharts 用本地的 `static/vendor/echarts.min.js`（断网也能用），
由 FastAPI 的 `StaticFiles` 和 `FileResponse` 托管。

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

## syslog 接入

除了 HTTP 上报，也支持接收真实设备发来的 syslog（UDP）。

### 启动接收器

```
.\.venv\Scripts\python.exe -m app.syslog.receiver
```

默认监听 `0.0.0.0:1514`（UDP）。这是**独立进程**，和 `uvicorn` 并行跑，两者共用 `logs.db`。

### 设备侧配置

Linux（rsyslog，写入 `/etc/rsyslog.d/50-forward.conf`）：

```
*.* @<宿主机IP>:1514
```

Cisco 交换机：`logging host <宿主机IP>`
华为交换机：`info-center loghost <宿主机IP>`

### 支持的报文格式

| 格式 | 说明 |
|---|---|
| RFC 3164 | 最常见的 BSD syslog，Linux 和多数网络设备默认用这个 |
| RFC 5424 | 新标准，能识别并提取主机名 |

解析失败（缺 PRI、PRI 越界、时间格式错）只记 warning 日志并跳过，**不会让接收器退出**。

### 幂等

`message_id` = `syslog:` + 报文内容的 SHA-256，重复投递的报文会被 `INSERT OR IGNORE` 忽略。

### ⚠️ Windows 收不到日志时先查这个

**Windows 防火墙里 Block 规则优先于 Allow 规则。** 某些软件会把 `python.exe` 的入站连接全部禁掉，这时加多少 Allow 规则都没用。

排查：

```
Get-NetFirewallRule -PolicyStore ActiveStore | Where-Object { $_.Action -eq "Block" -and $_.Direction -eq "Inbound" -and $_.Enabled -eq "True" } | Select-Object DisplayName, Profile
```

发现拦了 python 的规则就禁用：

```
Disable-NetFirewallRule -DisplayName "python.exe"
```

另外，`ping` 用的是 ICMP，和 UDP 是两套规则——**ping 不通不代表 syslog 收不到**。

