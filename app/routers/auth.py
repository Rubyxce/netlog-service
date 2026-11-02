"""注册与登录接口。

登录成功返回 JWT；之后受保护接口用 Authorization: Bearer <token> 访问。
"""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import get_conn
from app.security import TOKEN_TTL, create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/register", summary="注册新用户")
def register(body: RegisterIn, conn=Depends(get_conn)):
    username = body.username.strip()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少 3 个字符")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users(username, password_hash) VALUES (?, ?)",
            (username, hash_password(body.password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="用户名已存在")

    return {"id": cur.lastrowid, "username": username}


@router.post("/login", summary="登录，返回 JWT")
def login(body: LoginIn, conn=Depends(get_conn)):
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (body.username.strip(),),
    ).fetchone()

    # 故意不区分「用户不存在」和「密码错误」，防止用户名枚举
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token(row["id"], row["username"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": TOKEN_TTL,
    }
