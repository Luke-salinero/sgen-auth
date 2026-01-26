from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


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
    ENTITLEMENTS_BASE: str = os.getenv("ENTITLEMENTS_BASE", "http://127.0.0.1:8000")

    # ---- HTTP ----
    http_timeout_seconds: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))

    # ---- DB ----
    base_dir: Path = Path(__file__).resolve().parent.parent
    db_path: Path = Path(os.getenv("DB_PATH", str(base_dir / "data" / "auth.db")))
    db_foreign_keys_on: bool = _env_bool("DB_FOREIGN_KEYS_ON", True)
    db_busy_timeout_ms: int = int(os.getenv("DB_BUSY_TIMEOUT_MS", "5000"))

    jwt_issuer: str = _env("JWT_ISSUER", "http://127.0.0.1:8080/realms/sgen-test")
    jwt_audience: str = _env("JWT_AUDIENCE", "account")
    jwt_algorithms: tuple[str, ...] = tuple(
        os.getenv("JWT_ALGORITHMS", "RS256").split(",")
    )
    jwt_jwks_url: str = _env(
        "JWT_JWKS_URL",
        "http://127.0.0.1:8080/realms/sgen-test/protocol/openid-connect/certs",
    )
    jwt_public_key: str = _env("JWT_PUBLIC_KEY", "public_key")

    # Optional: small clock skew leeway (seconds) for exp/nbf checks
    jwt_leeway_seconds: int = int(os.getenv("JWT_LEEWAY_SECONDS", "0"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
