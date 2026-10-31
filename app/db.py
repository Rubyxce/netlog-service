"""本模块用于管理 logs.db的 连接和连接关闭"""
import sqlite3

DB_PATH = "logs.db"


def get_conn():
    """每来一个请求就开一个连接，请求结束自动关掉。

    yield 之前  = 请求开始时执行
    yield 之后  = 请求结束时执行（finally 保证一定执行）
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()