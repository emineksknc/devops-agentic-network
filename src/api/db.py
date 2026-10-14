"""SQLite kalicilik katmani. Basit tutuldu: stdlib sqlite3, WAL modu."""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

from src.config.settings import settings


def db_path() -> Path:
    # Goreceli yol CWD'ye degil PROJE KOKUNE sabitlenir; aksi halde server
    # farkli klasorden baslatilinca bos bir DB acar ve anahtarlar "gider".
    raw = getattr(settings, "DAN_DB_PATH", "data/dan.db")
    p = Path(raw)
    if not p.is_absolute():
        root = Path(__file__).resolve().parents[2]
        p = root / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                trigger TEXT NOT NULL DEFAULT 'api',
                repo TEXT NOT NULL,
                user_goal TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                dry_run INTEGER NOT NULL DEFAULT 1,
                final_report TEXT,
                error TEXT
            );
            CREATE TABLE IF NOT EXISTS commit_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(id),
                sha TEXT, short_sha TEXT, message TEXT, author TEXT,
                jira_ids TEXT NOT NULL DEFAULT '[]',
                code_changes TEXT,
                review_status TEXT, review_comment TEXT, affected_file TEXT
            );
            CREATE TABLE IF NOT EXISTS jira_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(id),
                commit_sha TEXT, ticket_id TEXT NOT NULL,
                review_passed INTEGER NOT NULL DEFAULT 1,
                code_changes TEXT,
                state TEXT NOT NULL DEFAULT 'planned',
                comment_ok INTEGER, transition_from TEXT,
                transition_to TEXT, transition_ok INTEGER,
                skipped_reason TEXT,
                target_status TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS policies (
                repo TEXT PRIMARY KEY,
                jira_project TEXT NOT NULL DEFAULT '',
                on_pass_transition TEXT NOT NULL DEFAULT 'In Review',
                on_fail_transition TEXT NOT NULL DEFAULT 'Blocked',
                auto_write_pass INTEGER NOT NULL DEFAULT 1,
                auto_write_fail INTEGER NOT NULL DEFAULT 0,
                require_approval INTEGER NOT NULL DEFAULT 1,
                dry_run_default INTEGER NOT NULL DEFAULT 1,
                github_conn_id TEXT NOT NULL DEFAULT '',
                jira_conn_id TEXT NOT NULL DEFAULT ''
            );
            -- Baglanti envanteri: birden fazla GitHub org / Jira sitesi.
            -- NOT(v1): token'lar duz metin durur; sonraki asamada vault/enc.
            CREATE TABLE IF NOT EXISTS connections (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                token TEXT NOT NULL DEFAULT '',
                project_key TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                temperature REAL NOT NULL DEFAULT 0.3,
                max_tokens INTEGER NOT NULL DEFAULT 2048,
                webhook_secret TEXT NOT NULL DEFAULT '',
                is_default INTEGER NOT NULL DEFAULT 0,
                is_disabled INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                disabled_at TEXT NOT NULL DEFAULT ''
            );
            -- Ajan ozellestirme: ac/kapa + system prompt override
            CREATE TABLE IF NOT EXISTS agent_configs (
                agent_name TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                system_prompt TEXT NOT NULL DEFAULT ''
            );
            -- Run olay gunlugu: dugum dugum ne yapildi (UI timeline)
            CREATE TABLE IF NOT EXISTS run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                node TEXT NOT NULL DEFAULT '',
                level TEXT NOT NULL DEFAULT 'info',
                message TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_events_run ON run_events(run_id);
            -- Global anahtar-deger ayarlar (redaksiyon vb.)
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
            -- Kullanicilar (Faz 1: login + roller). Ilk kayit admin olur.
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                created_at TEXT NOT NULL
            );
            -- Opak Bearer token'lar (sadece ozeti saklanir, ham token bir kez verilir)
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_units_run ON commit_units(run_id);
            CREATE INDEX IF NOT EXISTS idx_units_author ON commit_units(author);
            CREATE INDEX IF NOT EXISTS idx_actions_run ON jira_actions(run_id);
            CREATE INDEX IF NOT EXISTS idx_actions_ticket ON jira_actions(ticket_id);
            """
        )
        _migrate(conn)
        # NOT: otomatik tohumlama YOK. Kullanim karari: varsayilan baglanti
        # olusturulmaz; herkes (proje dahil) baglantisini UI/API ile ekler.
        # Bos DB = bos envanter, sablon mock degerleri UI tarafinda temizlenir.


def _migrate(conn: sqlite3.Connection) -> None:
    """Eski DB dosyalarina yeni sutunlari ekler (idempotent)."""

    def cols(table: str) -> set[str]:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    for table, wanted in {
        "runs": ["github_conn_id", "jira_conn_id", "llm_conn_id", "llm_provider", "llm_model", "finished_at"],
        "policies": ["github_conn_id", "jira_conn_id"],
        "connections": ["provider", "model", "temperature", "max_tokens", "webhook_secret",
                        "is_disabled", "created_at", "disabled_at",
                        "last_tested_at", "last_latency_ms", "last_test_ok"],
        "jira_actions": ["target_status", "approved_by", "approved_at"],
        "users": ["last_login_at"],
        "commit_units": ["jira_people"],
    }.items():
        have = cols(table)
        for col in wanted:
            if col not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
    _seal_legacy_secrets(conn)


def _seal_legacy_secrets(conn: sqlite3.Connection) -> None:
    """Acik metin kalmis token/secret'lari yerinde sifreler (tek yonlu migrasyon)."""
    from src.core import secrets as secrets_mod

    try:
        rows = conn.execute("SELECT id, token, webhook_secret FROM connections").fetchall()
    except Exception:
        return
    for r in rows:
        updates: dict[str, str] = {}
        if r["token"] and not secrets_mod.is_encrypted(r["token"]):
            updates["token"] = secrets_mod.encrypt(r["token"])
        if r["webhook_secret"] and not secrets_mod.is_encrypted(r["webhook_secret"]):
            updates["webhook_secret"] = secrets_mod.encrypt(r["webhook_secret"])
        for col, val in updates.items():
            conn.execute(f"UPDATE connections SET {col}=? WHERE id=?", (val, r["id"]))
    if rows:
        logger = logging.getLogger("dan.db")
        logger.info("Secret migrasyonu tamamlandi (%d baglanti tarandi).", len(rows))


def get_connection(conn: sqlite3.Connection, conn_id: str) -> Optional[dict[str, Any]]:
    from src.core import secrets as secrets_mod

    r = conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone()
    d = row_to_dict(r)
    if d:
        d["token"] = secrets_mod.decrypt(d.get("token") or "")
        d["webhook_secret"] = secrets_mod.decrypt(d.get("webhook_secret") or "")
    return d


def default_connection(conn: sqlite3.Connection, kind: str) -> Optional[dict[str, Any]]:
    from src.core import secrets as secrets_mod

    # Pasif baglantilar varsayilan secime girmez (acik secim get_connection ile hala mumkun)
    r = conn.execute(
        "SELECT * FROM connections WHERE kind=? AND is_default=1 AND is_disabled=0 LIMIT 1", (kind,)
    ).fetchone()
    if r is None:
        r = conn.execute("SELECT * FROM connections WHERE kind=? AND is_disabled=0 LIMIT 1", (kind,)).fetchone()
    d = row_to_dict(r)
    if d:
        d["token"] = secrets_mod.decrypt(d.get("token") or "")
        d["webhook_secret"] = secrets_mod.decrypt(d.get("webhook_secret") or "")
    return d


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    return dict(row) if row is not None else None


def loads(text: Any) -> Any:
    if not text:
        return []
    try:
        return json.loads(text)
    except Exception:
        return []
