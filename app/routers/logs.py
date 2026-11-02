from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_conn
from app.dependencies import verify_api_key, verify_token
from app.filters import LogFilter
from app.models import LogItem

# 不再在 router 上挂整体依赖：查询走 JWT（用户），上报走 API Key（设备）
router = APIRouter(
    prefix="/logs",
    tags=["logs"],
)

# 排序方向白名单：只允许升序和降序两种值
ORDER_DIRECTIONS = {"asc": "ASC", "desc": "DESC"}

@router.get("", dependencies=[Depends(verify_token)])
def get_logs(f: LogFilter = Depends(),
             n: int = Query(10, ge=1, le=100),
             page: int = Query(1, ge=1),
             order: str = Query("asc", pattern="^(asc|desc)$"),
             conn=Depends(get_conn)):
    """按过滤条件分页查询

    过滤参数见 app/filters.py：device / level / q / since / until
    """
    where_sql, params = f.sql()

    cur = conn.cursor()

    # 先查符合条件的总数（给前端显示「共 N 条」）
    cur.execute("SELECT COUNT(*) AS c FROM logs" + where_sql, params)
    total = cur.fetchone()["c"]

    # 再查当前这一页
    sql = "SELECT * FROM logs" + where_sql
    # 方向从白名单里取，不把请求参数原样拼进 SQL
    sql += " ORDER BY id " + ORDER_DIRECTIONS[order]
    sql += " LIMIT ? OFFSET ?"

    offset = (page - 1) * n
    cur.execute(sql, params + [n, offset])
    rows = cur.fetchall()

    data = [dict(row) for row in rows]

    return {"data": data, "page": page, "size": n, "total": total}


@router.post("", dependencies=[Depends(verify_api_key)])
def post_logs(logs: list[LogItem], conn=Depends(get_conn)):
    """批量上报，靠 message_id 唯一索引保证幂等

    设备（rsyslog / 交换机）不会登录，所以这里继续用 API Key。
    """
    allow_level = {"ERROR", "WARNING", "INFO", "DEBUG"}
    errors = []

    for idx, item in enumerate(logs):
        if item.level not in allow_level:
            errors.append(f"第{idx}条：level非法：{item.level}")
        if item.device.strip() == "":
            errors.append(f"第{idx}条：device不能为空")
        if item.message.strip() == "":
            errors.append(f"第{idx}条：message不能为空")
        if item.ts.strip() == "":
            errors.append(f"第{idx}条：ts不能为空")

    if errors:
        raise HTTPException(status_code=400, detail=" | ".join(errors))

    insert_data = []
    for item in logs:
        d = item.model_dump()
        insert_data.append(
            (str(d["message_id"]), d["device"], d["level"], d["message"], d["ts"])
        )

    cur = conn.cursor()
    cur.executemany(
        "INSERT OR IGNORE INTO logs(message_id,device,level,message,ts) "
        "VALUES (?,?,?,?,?)",
        insert_data,
    )
    conn.commit()

    return {"inserted": cur.rowcount}


@router.get("/{log_id}", dependencies=[Depends(verify_token)])
def get_logs_by_id(log_id: int = 0, conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs WHERE id = ?", (log_id,))
    row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Log not found")
    else:
        return {"log": dict(row)}