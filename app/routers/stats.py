from fastapi import APIRouter, Depends

from app.db import get_conn
from app.dependencies import verify_token
from app.filters import LogFilter

router = APIRouter(
    tags=["stats"],
    dependencies=[Depends(verify_token)],
)


@router.get("/stats")
def get_stats(f: LogFilter = Depends(), conn=Depends(get_conn)):
    """按级别、按设备统计（支持和 /logs 一样的过滤条件）"""
    where_sql, params = f.sql()
    cur = conn.cursor()

    cur.execute(
        "SELECT level, COUNT(*) AS cnt FROM logs" + where_sql + " GROUP BY level",
        params,
    )
    rows_level = cur.fetchall()
    by_level = {level: cnt for level, cnt in rows_level}

    cur.execute(
        "SELECT device, COUNT(*) AS cnt FROM logs" + where_sql + " GROUP BY device",
        params,
    )
    rows_device = cur.fetchall()
    by_device = {device: cnt for device, cnt in rows_device}

    return {"by_level": by_level, "by_device": by_device}
