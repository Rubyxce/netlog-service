from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_conn
from app.dependencies import verify_api_key
from app.models import LogItem

router = APIRouter(
    prefix="/logs",
    tags=["logs"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("")
def get_logs(device: str = None, level: str = None,
             n: int = Query(10, ge=1, le=100),
             page: int = Query(1, ge=1),
             conn=Depends(get_conn)):
    """按设备/级别过滤 + 分页"""
    sql = "SELECT * FROM logs"
    params = []
    conditions = []

    if device is not None:
        conditions.append("device = ?")
        params.append(device)

    if level is not None:
        conditions.append("level = ?")
        params.append(level)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id"

    offset = (page - 1) * n
    sql += " LIMIT ? OFFSET ?"
    params.append(n)
    params.append(offset)

    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()

    data = [dict(row) for row in rows]

    return {"data": data, "page": page, "size": n}


@router.post("")
def post_logs(logs: list[LogItem], conn=Depends(get_conn)):
    """批量上报，靠 message_id 唯一索引保证幂等"""
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


@router.get("/{log_id}")
def get_logs_by_id(log_id: int = 0, conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs WHERE id = ?", (log_id,))
    row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Log not found")
    else:
        return {"log": dict(row)}