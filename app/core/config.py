from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    # ---- Keycloak ----
    keycloak_base: str = os.getenv("KEYCLOAK_BASE", "http://127.0.0.1:8080")
    keycloak_realm: str = os.getenv("KEYCLOAK_REALM", "sgen-test")

    # ---- Optional validator hop ----
    validator_base: str = os.getenv("VALIDATOR_BASE", "http://127.0.0.1:9100")

    # ---- HTTP ----
    http_timeout_seconds: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))

    # ---- DB ----
    base_dir: Path = Path(__file__).resolve().parent.parent
    db_path: Path = Path(os.getenv("DB_PATH", str(base_dir / "data" / "auth.db")))
    db_foreign_keys_on: bool = _env_bool("DB_FOREIGN_KEYS_ON", True)
    db_busy_timeout_ms: int = int(os.getenv("DB_BUSY_TIMEOUT_MS", "5000"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
