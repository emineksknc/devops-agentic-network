"""Kimlik dogrulama: pbkdf2 parola + opak Bearer token. Yeni bagimlilik yok (stdlib)."""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api import db

logger = logging.getLogger("dan.auth")

_PEPPER = "dan-auth-v1"
_PBKDF2_ROUNDS = 200_000
TOKEN_TTL_DAYS = 30

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", (_PEPPER + password).encode(), salt.encode(), _PBKDF2_ROUNDS)
    return f"pbkdf2$sha256${_PBKDF2_ROUNDS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, _, rounds, salt, hexhash = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", (_PEPPER + password).encode(), salt.encode(), int(rounds))
        return hmac.compare_digest(dk.hex(), hexhash)
    except Exception:
        return False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mint_token(user_id: str) -> str:
    raw = "dan_" + secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    exp = (datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)).isoformat()
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?,?,?,?)",
            (digest, user_id, _now(), exp),
        )
    return raw


def revoke_token(raw: str) -> None:
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with db.connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (digest,))


def _user_by_session(raw: str) -> Optional[dict]:
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with db.connect() as conn:
        s = db.row_to_dict(conn.execute(
            "SELECT * FROM sessions WHERE token_hash=?", (digest,)).fetchone())
        if not s:
            return None
        try:
            if datetime.fromisoformat(s["expires_at"]) < datetime.now(timezone.utc):
                conn.execute("DELETE FROM sessions WHERE token_hash=?", (digest,))
                return None
        except Exception:
            return None
        u = db.row_to_dict(conn.execute(
            "SELECT id, username, role, created_at FROM users WHERE id=?", (s["user_id"],)).fetchone())
        return u


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    if not creds or not creds.credentials:
        raise HTTPException(401, "giris gerekli (Bearer token)")
    user = _user_by_session(creds.credentials)
    if not user:
        raise HTTPException(401, "token gecersiz veya suresi dolmus")
    return user


def require_roles(*roles: str):
    async def guard(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(403, "bu islem icin yetki yok")
        return user

    return guard
