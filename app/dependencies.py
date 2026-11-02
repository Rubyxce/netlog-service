import logging
import os

from fastapi import Header, HTTPException

from app.security import TokenError, decode_token

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


def verify_token(authorization: str = Header(None)):
    """校验 Authorization: Bearer <JWT>，返回 token 里的 payload。

    浏览器侧用这个；设备上报（POST /logs）仍然用 verify_api_key。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="missing token")

    # 格式必须是 "Bearer xxx"
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="bad authorization header")

    try:
        payload = decode_token(token)
    except TokenError as e:
        # 签名不对 / 格式不对 / 已过期，都统一 401
        raise HTTPException(status_code=401, detail=f"invalid token: {e}")

    return payload

