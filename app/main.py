import logging
import time

from fastapi import FastAPI, Request

from app.routers import logs, stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="netlog-service")


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