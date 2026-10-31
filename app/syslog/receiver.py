import hashlib
import logging
import socket
import sqlite3

from app.db import DB_PATH
from app.syslog.parser import parse

# 全局日志基础配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

HOST = "0.0.0.0"
PORT = 1514

def make_message_id(raw):
    """报文 hash 做幂等键 加来源前缀"""
    return "syslog:" + hashlib.sha256(raw).hexdigest()

def insert_log(conn, result, raw):
    """返回实际插入的行数 1 成功 0 跳过"""
    cur = conn.execute(
        "INSERT OR IGNORE INTO logs(message_id,device,level,message,ts) "
        "VALUES (?,?,?,?,?)",
        (make_message_id(raw), result["host"], result["level"],
         result["message"], result["ts"]),
    )
    return cur.rowcount

def run():

    # 创建UDP socket IPv4协议族
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 设置内核接收缓冲区大小 1MB 防止高并发丢包
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
    # 绑定地址端口，开始监听；打印启动日志
    sock.bind((HOST, PORT))
    logger.info("syslog 接收器启动，监听 %s:%d",HOST,PORT)
    # 打开sqlite连接 定义三个计数器
    conn = sqlite3.connect(DB_PATH)
    inserted = 0            #成功新增入库
    duplicated = 0          #重复报文
    rejected = 0            #报文解析失败


    try:
        while True:
            """主循环，data用于接收报文 addr接收 来源IP+源端口"""
            data,addr = sock.recvfrom(4096)
            # 接受解析的报文
            parsed = parse(data)
            if not parsed["ok"]:
                rejected += 1
                logger.warning("坏包 from %s: %s",addr,parsed["reason"])
                # 识别到坏包直接跳到下一次循环，防止接收器崩溃
                continue

            if insert_log(conn, parsed, data):
                inserted += 1

            else:
                duplicated += 1

            conn.commit()

            total = inserted + duplicated + rejected
            if total and total % 100 == 0:
                logger.info("累计：入库%d，重复%d，拒收%d",
                            inserted,duplicated,rejected)

    except KeyboardInterrupt:
        logger.info("收到 Ctrl+C ，退出")

    finally:
        conn.commit()
        conn.close()
        sock.close()


if __name__ == "__main__":
    run()
