from fastapi import APIRouter, Depends

from app.db import get_conn
from app.dependencies import verify_api_key

router = APIRouter(
    tags=["stats"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/stats")
def get_stats(device: str = None, level: str = None, conn=Depends(get_conn)):
    cur = conn.cursor()

    cur.execute("SELECT level, COUNT(*) AS cnt FROM logs GROUP BY level")
    rows_level = cur.fetchall()
    by_level = {level: cnt for level, cnt in rows_level}

    cur.execute("SELECT device, COUNT(*) AS cnt FROM logs GROUP BY device")
    rows_device = cur.fetchall()
    by_device = {device: cnt for device, cnt in rows_device}

    return {"by_level": by_level, "by_device": by_device}