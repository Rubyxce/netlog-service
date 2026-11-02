"""JWT 与密码哈希：只用标准库，零依赖。

JWT 就是一个三段式字符串：
    header.payload.signature

- header   ：说明用什么算法（HS256）
- payload  ：真正的内容（用户 id、过期时间）
- signature：用密钥对 "header.payload" 做的 HMAC 签名
"""
import base64
import hashlib
import hmac
import json
import os
import time

# 签名密钥：从环境变量读，不写死在代码里（写死 = 任何人都能伪造 token）
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
TOKEN_TTL = 3600          # token 有效期（秒）

PBKDF2_ITERATIONS = 100_000


# ---------- base64url ----------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


# ---------- 签名 ----------

def _sign(message: str) -> str:
    digest = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
    return _b64url_encode(digest)


# ---------- 签发 ----------

def create_token(user_id: int, username: str, ttl: int = TOKEN_TTL) -> str:
    """签发 token。

    payload 里的标准字段：
        sub  subject，用户标识
        iat  issued at，签发时间
        exp  expiration，过期时间（Unix 时间戳，秒）
    """
    now = int(time.time())
    header = {"alg": JWT_ALG, "typ": "JWT"}
    payload = {"sub": user_id, "username": username, "iat": now, "exp": now + ttl}

    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    s = _sign(f"{h}.{p}")
    return f"{h}.{p}.{s}"


# ---------- 校验 ----------

class TokenError(Exception):
    """token 不合法时抛出，调用方转成 401"""


def decode_token(token: str) -> dict:
    """验签 + 解析 + 检查过期，任何一步失败都抛 TokenError"""
    try:
        h, p, s = token.split(".")
    except ValueError:
        raise TokenError("token 格式错误，不是三段")

    # 1. 验签：用同样的算法重算一遍，对比是否一致
    #    compare_digest 防「时序攻击」（逐字符比较会泄露前缀）
    expected = _sign(f"{h}.{p}")
    if not hmac.compare_digest(expected, s):
        raise TokenError("签名不对")

    # 2. 解析 payload
    try:
        payload = json.loads(_b64url_decode(p))
    except (ValueError, json.JSONDecodeError):
        raise TokenError("payload 不是合法 JSON")

    # 3. 检查过期
    if payload.get("exp", 0) < time.time():
        raise TokenError("token 已过期")

    return payload


# ---------- 密码哈希 ----------
# 不存明文密码。PBKDF2-HMAC-SHA256：加盐 + 迭代 10 万次。

def hash_password(password: str) -> str:
    """返回 'salt$hash' 字符串，直接存进数据库"""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """用同样的盐和迭代次数重算，和存的值比"""
    try:
        salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False

    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(actual, expected)
