from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(
    db_path: Path,
    foreign_keys_on: bool = True,
    busy_timeout_ms: int = 5000,
) -> sqlite3.Connection:
    """
    Create and return an SQLite connection
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)};")
    conn.execute(f"PRAGMA foreign_keys = {1 if foreign_keys_on else 0};")

    return conn
