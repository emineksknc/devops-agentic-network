"""SQLite kalicilik katmani. Basit tutuldu: stdlib sqlite3, WAL modu."""
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from src.config.settings import settings


def db_path() -> Path:
    p = Path(getattr(settings, "DAN_DB_PATH", "data/dan.db"))
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
                skipped_reason TEXT
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
                is_default INTEGER NOT NULL DEFAULT 0
            );
            -- Ajan ozellestirme: ac/kapa + system prompt override
            CREATE TABLE IF NOT EXISTS agent_configs (
                agent_name TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                system_prompt TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_units_run ON commit_units(run_id);
            CREATE INDEX IF NOT EXISTS idx_units_author ON commit_units(author);
            CREATE INDEX IF NOT EXISTS idx_actions_run ON jira_actions(run_id);
            CREATE INDEX IF NOT EXISTS idx_actions_ticket ON jira_actions(ticket_id);
            """
        )
        _migrate(conn)
        _seed_default_connections(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Eski DB dosyalarina yeni sutunlari ekler (idempotent)."""

    def cols(table: str) -> set[str]:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    for table, wanted in {
        "runs": ["github_conn_id", "jira_conn_id", "llm_conn_id"],
        "policies": ["github_conn_id", "jira_conn_id"],
        "connections": ["provider", "model"],
    }.items():
        have = cols(table)
        for col in wanted:
            if col not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")


def _seed_default_connections(conn: sqlite3.Connection) -> None:
    """Env'deki tekil ayarlari default baglanti olarak tohumla (sadece bosken)."""
    existing = conn.execute("SELECT COUNT(*) c FROM connections").fetchone()["c"]
    if existing:
        return
    conn.execute(
        "INSERT INTO connections (id, kind, name, base_url, owner, email, token, project_key, is_default)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        ("github-default", "github", "Default GitHub", "https://api.github.com",
         settings.GITHUB_OWNER, "", settings.GITHUB_TOKEN, "", 1),
    )
    conn.execute(
        "INSERT INTO connections (id, kind, name, base_url, owner, email, token, project_key, is_default)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        ("jira-default", "jira", "Default Jira", settings.JIRA_DOMAIN,
         "", settings.JIRA_USER_EMAIL, settings.JIRA_API_TOKEN, settings.JIRA_PROJECT_KEY, 1),
    )
    conn.execute(
        "INSERT INTO connections (id, kind, name, base_url, owner, email, token, project_key, provider, model, is_default)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("llm-default", "llm", "Default LLM", getattr(settings, "OLLAMA_HOST", "http://localhost:11434"),
         "", "", getattr(settings, "LLM_API_KEY", ""), "",
         getattr(settings, "LLM_PROVIDER", "ollama"), settings.LLM_MODEL, 1),
    )


def get_connection(conn: sqlite3.Connection, conn_id: str) -> Optional[dict[str, Any]]:
    r = conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone()
    return row_to_dict(r)


def default_connection(conn: sqlite3.Connection, kind: str) -> Optional[dict[str, Any]]:
    r = conn.execute(
        "SELECT * FROM connections WHERE kind=? AND is_default=1 LIMIT 1", (kind,)
    ).fetchone()
    if r is None:
        r = conn.execute("SELECT * FROM connections WHERE kind=? LIMIT 1", (kind,)).fetchone()
    return row_to_dict(r)


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    return dict(row) if row is not None else None


def loads(text: Any) -> Any:
    if not text:
        return []
    try:
        return json.loads(text)
    except Exception:
        return []
