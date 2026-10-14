"""Kullanici kayit/giris/cikis. Ilk kayit admin olur, sonrakiler viewer."""
import re
import uuid
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api import db
from src.api.schemas import TokenOut, UserIn, UserOut
from src.core import auth as auth_core
from src.core.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.@-]{3,32}$")


def _to_out(r: dict) -> UserOut:
    return UserOut(id=r["id"], username=r["username"], role=r["role"], created_at=r["created_at"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    body: UserIn,
    opt: dict | None = Depends(auth_core.get_optional_user),
) -> UserOut:
    """Kayit DAVET usuludur: ilk kullanici (bos DB) herkese acik admin olur,
    sonrakileri yalnizca admin acar."""
    if not _USERNAME_RE.match(body.username):
        raise HTTPException(400, "kullanici adi 3-32 karakter (harf/rakam/._@-) olmali")
    with db.connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if count > 0 and (not opt or opt.get("role") != "admin"):
            raise HTTPException(401 if not opt else 403,
                                "kayit kapali: yeni kullaniciyi admin acar" if opt else "giris gerekli")
        exists = conn.execute("SELECT id FROM users WHERE username=?", (body.username,)).fetchone()
        if exists:
            raise HTTPException(409, "bu kullanici adi alinmis")
        role = "admin" if count == 0 else "viewer"
        uid = uuid.uuid4().hex[:8]
        now = auth_core._now()
        conn.execute(
            "INSERT INTO users (id, username, password_hash, role, created_at) VALUES (?,?,?,?,?)",
            (uid, body.username, auth_core.hash_password(body.password), role, now),
        )
        row = db.row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    return _to_out(row)


@router.get("/users", response_model=list[UserOut])
async def list_users(_admin: dict = Depends(auth_core.require_roles("admin"))) -> list[UserOut]:
    with db.connect() as conn:
        rows = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at").fetchall()
    return [UserOut(id=r["id"], username=r["username"], role=r["role"], created_at=r["created_at"]) for r in rows]


@router.post("/login", response_model=TokenOut)
async def login(body: UserIn) -> TokenOut:
    with db.connect() as conn:
        row = db.row_to_dict(conn.execute(
            "SELECT * FROM users WHERE username=?", (body.username,)).fetchone())
    if not row or not auth_core.verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "kullanici adi veya parola hatali")
    token = auth_core.mint_token(row["id"])
    return TokenOut(token=token, user=_to_out(row))


@router.post("/logout")
async def logout(
    user: dict = Depends(get_current_user),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if creds and creds.credentials:
        auth_core.revoke_token(creds.credentials)
    return {"ok": True, "user": user["username"]}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)) -> UserOut:
    return UserOut(**user)


@router.put("/users/{user_id}", response_model=UserOut)
async def set_role(user_id: str, body: dict, admin: dict = Depends(auth_core.require_roles("admin"))) -> UserOut:
    role = (body.get("role") or "").strip()
    if role not in ("admin", "approver", "viewer"):
        raise HTTPException(400, "rol admin/approver/viewer olmali")
    with db.connect() as conn:
        cur = conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "kullanici bulunamadi")
        row = db.row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
    return _to_out(row)
