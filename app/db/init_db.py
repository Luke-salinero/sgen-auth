from __future__ import annotations

from pathlib import Path

from app.core import get_settings
from app.db.connection import get_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def init_db() -> None:
    settings = get_settings()
    conn = get_connection(
        db_path=settings.db_path,
        foreign_keys_on=settings.db_foreign_keys_on,
        busy_timeout_ms=settings.db_busy_timeout_ms,
    )
    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
