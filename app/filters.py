"""日志过滤条件：/logs 和 /stats 共用。

两个接口的过滤参数完全一样，如果各写一份，以后加一个参数要改两处，
必然漏一处。所以抽成 FastAPI 依赖。

用法：

    def get_logs(f: LogFilter = Depends(), ...):
        where_sql, params = f.sql()
        cur.execute("SELECT * FROM logs" + where_sql, params)
"""
from fastapi import Query


class LogFilter:
    """从查询参数里解析过滤条件，生成 SQL 片段。

    device ：设备名，精确匹配
    level  ：级别，精确匹配
    q      ：消息关键字，LIKE 模糊匹配
    since  ：起始日期 YYYY-MM-DD（含）
    until  ：结束日期 YYYY-MM-DD（含）
    """

    def __init__(
        self,
        device: str = None,
        level: str = None,
        q: str = None,
        since: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
        until: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    ):
        self.device = device
        self.level = level
        self.q = q
        self.since = since
        self.until = until

    def sql(self):
        """返回 (where_sql, params)。

        没有条件时 where_sql 是空字符串，拼进 SQL 就是 "SELECT * FROM logs"。
        """
        conditions = []
        params = []

        if self.device is not None:
            conditions.append("device = ?")
            params.append(self.device)

        if self.level is not None:
            conditions.append("level = ?")
            params.append(self.level)

        if self.q:
            conditions.append("message LIKE ?")
            params.append(f"%{self.q}%")

        # ts 存的是 "2026-10-31 11:12:15"，取前 10 位就是日期。
        # YYYY-MM-DD 的字符串比较等价于日期比较，不用 date() 函数。
        if self.since:
            conditions.append("substr(ts, 1, 10) >= ?")
            params.append(self.since)

        if self.until:
            conditions.append("substr(ts, 1, 10) <= ?")
            params.append(self.until)

        where_sql = ""
        if conditions:
            where_sql = " WHERE " + " AND ".join(conditions)

        return where_sql, params
