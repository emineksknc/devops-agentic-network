"""Basit secret redaksiyonu: LLM'e giden diff'lerdeki bariz kimlikleri maskeler.
app_settings.redact_secrets=1 iken Jira ozetleri ve raporlar icin uygulanir.
"""
import re

PATTERNS = [
    r"(ghp_[A-Za-z0-9]{10,})",
    r"(github_pat_[A-Za-z0-9_]{10,})",
    r"(xox[bpas]-[A-Za-z0-9-]{6,})",
    r"(AKIA[0-9A-Z]{16})",
    r"(?i)(api[_-]?key\s*[:=]\s*['\"]?)([^'\"\s;,]{6,})(['\"]?)",
    r"(?i)(password\s*[:=]\s*['\"]?)([^'\"\s;,]{4,})(['\"]?)",
    r"(?i)(secret\s*[:=]\s*['\"]?)([^'\"\s;,]{6,})(['\"]?)",
    r"(Bearer\s+)([A-Za-z0-9\-._~+/=]{10,})",
]


def redact(text: str) -> str:
    if not text:
        return text
    out = text
    for p in PATTERNS:
        try:
            if "(" in p and p.count("(") > 1:
                out = re.sub(p, lambda m: m.group(1) + "***REDACTED***" + (m.group(3) if m.lastindex and m.lastindex >= 3 else ""), out)
            else:
                out = re.sub(p, "***REDACTED***", out)
        except Exception:
            continue
    return out


def is_enabled() -> bool:
    try:
        from src.api import db as dbmod

        with dbmod.connect() as conn:
            r = conn.execute("SELECT value FROM app_settings WHERE key='redact_secrets'").fetchone()
            if r is None:
                return True  # varsayilan acik
            return (r["value"] or "").lower() not in ("0", "false", "no")
    except Exception:
        return True
