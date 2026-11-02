"""模拟设备持续上报日志（让页面上的数字动起来）。

走真实的 HTTP 接口 POST /logs，所以会经过：
    鉴权（X-Api-Key）→ Pydantic 校验 → 幂等（message_id 唯一索引）→ 入库

用法（另开一个终端，服务要先跑起来）：

    python simulate.py                    # 每 2 秒 1 条，一直跑
    python simulate.py --interval 0.5     # 每 0.5 秒 1 条
    python simulate.py --count 50         # 只发 50 条就停
    python simulate.py --batch 3          # 每次上报 3 条

环境变量：
    API_KEY     默认 dev-key，要和启动服务时的值一致
    NETLOG_URL  默认 http://127.0.0.1:8000/logs
"""
import argparse
import json
import os
import random
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime

URL = os.getenv("NETLOG_URL", "http://127.0.0.1:8000/logs")
API_KEY = os.getenv("API_KEY", "dev-key")

DEVICES = ["sw1", "sw2", "sw3", "sw4", "fw1", "core1"]

# 按级别给不同的消息池，比随机组合更像真实网络设备
MESSAGES = {
    "ERROR": [
        "interface GigabitEthernet0/1 down",
        "bgp peer 10.0.0.2 timeout",
        "cpu usage 96%",
        "link flap detected on port 3",
        "packet loss 7% on uplink",
    ],
    "WARNING": [
        "temperature 68C above threshold",
        "memory usage 85%",
        "ospf neighbor renegotiation",
        "fan speed abnormal",
    ],
    "INFO": [
        "ospf up on vlan 10",
        "configuration saved",
        "user admin login from 192.168.1.5",
        "ntp synchronized",
    ],
    "DEBUG": [
        "acl rule hit",
        "queue drained",
        "packet forwarded to next hop",
        "arp entry refreshed",
    ],
}

LEVEL_WEIGHTS = [("INFO", 40), ("WARNING", 25), ("ERROR", 20), ("DEBUG", 15)]


def pick_level():
    """按权重挑级别，让 INFO 最多、DEBUG 最少，接近真实网络"""
    levels, weights = zip(*LEVEL_WEIGHTS)
    return random.choices(levels, weights=weights, k=1)[0]


def build_one():
    level = pick_level()
    return {
        "message_id": str(uuid.uuid4()),
        "device": random.choice(DEVICES),
        "level": level,
        "message": random.choice(MESSAGES[level]),
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def post(logs):
    """发一批日志，返回后端响应；失败抛异常"""
    body = json.dumps(logs).encode("utf-8")
    req = urllib.request.Request(URL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Api-Key", API_KEY)

    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="模拟设备持续上报日志")
    parser.add_argument("--interval", type=float, default=2.0, help="每次上报间隔（秒），默认 2")
    parser.add_argument("--batch", type=int, default=1, help="每次上报几条，默认 1")
    parser.add_argument("--count", type=int, default=0, help="总共上报几批，0 = 无限")
    args = parser.parse_args()

    print(f"目标: {URL}")
    print(f"间隔: {args.interval}s   每批: {args.batch} 条   总数: {args.count or '无限'}")
    print("Ctrl+C 停止\n")

    sent_batches = 0
    sent_logs = 0
    try:
        while True:
            batch = [build_one() for _ in range(args.batch)]
            try:
                result = post(batch)
                inserted = result.get("inserted", 0)
                sent_logs += inserted
                sent_batches += 1
                first = batch[0]
                print(f"[{sent_batches:>4}] {first['ts']}  {first['device']:<6} "
                      f"{first['level']:<7} {first['message'][:40]:<40} +{inserted}")
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:200]
                print(f"HTTP {e.code}: {body}")
                if e.code == 401:
                    print("→ API Key 不对。检查 --api-key 或环境变量 API_KEY")
                    break
            except urllib.error.URLError as e:
                print(f"连不上 {URL}: {e.reason}")
                print("→ 服务没启动？先跑 uvicorn main:app --reload")
                break

            if args.count and sent_batches >= args.count:
                break

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print()

    print(f"\n结束：{sent_batches} 批，共插入 {sent_logs} 条")


if __name__ == "__main__":
    main()
