import logging
import os

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)

# 启动时读一次 没配就是 None
API_KEY = os.getenv("API_KEY")


def verify_api_key(x_api_key: str = Header(None)):
    """校验请求头 X-Api-Key 不对就抛 401，不进业务逻辑。"""
    if API_KEY is None:
        # 服务端自己没配好，不是客户端的错 → 500
        logger.error("环境变量 API_KEY 未配置，所有鉴权请求都会被拒绝")
        raise HTTPException(status_code=500, detail="server not configured")

    if x_api_key != API_KEY:
        # 没给 / 给错 → 401
        raise HTTPException(status_code=401, detail="invalid api key")

    return True
