import logging
import time
from pathlib import Path
from fastapi import FastAPI, Request
from app.routers import logs, stats
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 项目根目录（app/ 的上一层）。用绝对路径，从哪个目录启动服务都能找到 static/
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

logger = logging.getLogger(__name__)

app = FastAPI(title="netlog-service")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.middleware("http")
async def log_request(request: Request, call_next):
    """每个请求进出都经过这里，记录方法/路径/状态码/耗时"""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        cost = (time.perf_counter() - start) * 1000
        logger.exception("异常 %s %s 500 %.1fms",
                         request.method, request.url.path, cost)
        raise

    cost = (time.perf_counter() - start) * 1000
    logger.info("%s %s %d %.1fms",
                request.method, request.url.path, response.status_code, cost)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(logs.router)
app.include_router(stats.router)