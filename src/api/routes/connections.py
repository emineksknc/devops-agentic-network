"""Baglanti envanteri: birden fazla GitHub org / Jira sitesi / LLM.
NOT(v1): token'lar SQLite'da duz metin durur; dosya izni + vault plani sart."""
import uuid

from fastapi import APIRouter, HTTPException

from src.api import db
from src.api.schemas import ConnectionIn, ConnectionOut

router = APIRouter(prefix="/api/connections", tags=["connections"])


MASKED = "***masked***"


def _to_out(r) -> ConnectionOut:
    # Token ASLA listeleme/get ile disari verilmez
    return ConnectionOut(
        id=r["id"], name=r["name"], kind=r["kind"], base_url=r["base_url"] or "",
        owner=r["owner"] or "", email=r["email"] or "",
        token=MASKED if r["token"] else "",
        project_key=r["project_key"] or "", is_default=bool(r["is_default"]),
    )


@router.get("", response_model=list[ConnectionOut])
async def list_connections(kind: str = "") -> list[ConnectionOut]:
    with db.connect() as conn:
        if kind:
            rows = conn.execute("SELECT * FROM connections WHERE kind=? ORDER BY name", (kind,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM connections ORDER BY kind, name").fetchall()
    return [_to_out(r) for r in rows]


@router.post("", response_model=ConnectionOut, status_code=201)
async def create_connection(body: ConnectionIn) -> ConnectionOut:
    conn_id = f"{body.kind}-{uuid.uuid4().hex[:6]}"
    with db.connect() as conn:
        if body.is_default:
            conn.execute("UPDATE connections SET is_default=0 WHERE kind=?", (body.kind,))
        conn.execute(
            "INSERT INTO connections (id, kind, name, base_url, owner, email, token, project_key, is_default)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (conn_id, body.kind, body.name, body.base_url, body.owner, body.email,
             body.token, body.project_key, int(body.is_default)),
        )
    return ConnectionOut(id=conn_id, **body.model_dump())


@router.put("/{conn_id}", response_model=ConnectionOut)
async def update_connection(conn_id: str, body: ConnectionIn) -> ConnectionOut:
    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone())
        if not r:
            raise HTTPException(404, "baglanti bulunamadi")
        # Maskeli/bos token gelirse mevcut secret korunur
        token = r["token"] if body.token in ("", MASKED) else body.token
        if body.is_default:
            conn.execute("UPDATE connections SET is_default=0 WHERE kind=?", (r["kind"],))
        conn.execute(
            """UPDATE connections SET name=?, base_url=?, owner=?, email=?, token=?,
               project_key=?, is_default=? WHERE id=?""",
            (body.name, body.base_url, body.owner, body.email, token,
             body.project_key, int(body.is_default), conn_id),
        )
    out = body.model_dump()
    out["token"] = MASKED if token else ""
    return ConnectionOut(id=conn_id, **out)


@router.delete("/{conn_id}")
async def delete_connection(conn_id: str) -> dict:
    with db.connect() as conn:
        cur = conn.execute("DELETE FROM connections WHERE id=?", (conn_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "baglanti bulunamadi")
    return {"deleted": conn_id}
