import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional, Tuple

OwnerType = Literal["user", "workspace"]
Status = Literal["active", "revoked"]


@dataclass(frozen=True)
class ApiKeyRow:
    id: str
    owner_type: OwnerType
    owner_id: str
    name: str
    api_key: str
    keycloak_client_id: str
    status: Status
    created_by_user_id: Optional[str]
    created_at: str
    last_used_at: Optional[str]
    revoked_at: Optional[str]


def _row_to_api_key(row: sqlite3.Row) -> ApiKeyRow:
    return ApiKeyRow(
        id=row["id"],
        owner_type=row["owner_type"],
        owner_id=row["owner_id"],
        name=row["name"],
        api_key=row["api_key"],
        keycloak_client_id=row["keycloak_client_id"],
        status=row["status"],
        created_by_user_id=row["created_by_user_id"],
        created_at=row["created_at"],
        last_used_at=row["last_used_at"],
        revoked_at=row["revoked_at"],
    )


class AuthRepo:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_api_key_by_client_id(self, client_id: str) -> Optional[ApiKeyRow]:
        sql = """
        SELECT
          id, owner_type, owner_id, name, api_key, keycloak_client_id, status,
          created_by_user_id, created_at, last_used_at, revoked_at
        FROM api_keys
        WHERE keycloak_client_id = ?
        LIMIT 1
        """
        cur = self._conn.execute(sql, (client_id,))
        row = cur.fetchone()
        return _row_to_api_key(row) if row else None

    def get_api_key_by_api_key(self, api_key: str) -> Optional[ApiKeyRow]:
        sql = """
        SELECT
          id, owner_type, owner_id, name, api_key, keycloak_client_id, status,
          created_by_user_id, created_at, last_used_at, revoked_at
        FROM api_keys
        WHERE api_key = ?
        LIMIT 1
        """
        cur = self._conn.execute(sql, (api_key,))
        row = cur.fetchone()
        return _row_to_api_key(row) if row else None

    def list_api_keys(self, owner_type: OwnerType, owner_id: str) -> list[ApiKeyRow]:
        sql = """
        SELECT
          id, owner_type, owner_id, name, api_key, keycloak_client_id, status,
          created_by_user_id, created_at, last_used_at, revoked_at
        FROM api_keys
        WHERE owner_type = ? AND owner_id = ?
        ORDER BY created_at DESC
        """
        cur = self._conn.execute(sql, (owner_type, owner_id))
        return [_row_to_api_key(r) for r in cur.fetchall()]

    def create_api_key(
        self,
        *,
        key_id: str,
        owner_type: OwnerType,
        owner_id: str,
        name: str,
        api_key: str,
        keycloak_client_id: str,
        created_by_user_id: Optional[str] = None,
    ) -> None:
        sql = """
        INSERT INTO api_keys (
          id, owner_type, owner_id, name, api_key, keycloak_client_id,
          status, created_by_user_id
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
        """
        self._conn.execute(
            sql,
            (
                key_id,
                owner_type,
                owner_id,
                name,
                api_key,
                keycloak_client_id,
                created_by_user_id,
            ),
        )

    def revoke_api_key(self, key_id: str) -> None:
        sql = """
        UPDATE api_keys
        SET status = 'revoked',
            revoked_at = (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        WHERE id = ? AND status != 'revoked'
        """
        self._conn.execute(sql, (key_id,))

    def touch_last_used(self, client_id: str) -> None:
        sql = """
        UPDATE api_keys
        SET last_used_at = (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        WHERE keycloak_client_id = ? AND status = 'active'
        """
        self._conn.execute(sql, (client_id,))

    def upsert_api_key_from_claims(
        self,
        claims: Mapping[str, Any],
        *,
        api_key: str,
        keycloak_client_id_override: Optional[str] = None,
    ) -> None:

        api_key_id = claims.get("sub")
        if not api_key_id:
            raise ValueError("JWT missing required claim: sub")

        keycloak_client_id = keycloak_client_id_override or claims.get("client_id")

        if not keycloak_client_id:
            raise ValueError("Missing required keycloak client id")
        owner_id = claims.get("sub")

        sql = """
        INSERT INTO api_keys (
        id, owner_type, owner_id, name,api_key,keycloak_client_id,status,last_used_at
        )
        VALUES (
        :id, :owner_type, :owner_id, :name, :api_key, :keycloak_client_id, 'active',
        strftime('%Y-%m-%dT%H:%M:%fZ','now')
        )
        ON CONFLICT(keycloak_client_id) DO UPDATE SET
        id = excluded.id,
        last_used_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
        status = 'active',
        owner_type = excluded.owner_type,
        owner_id = excluded.owner_id,
        name = excluded.name,
        api_key = excluded.api_key,
        revoked_at = NULL;
        """

        params = {
            "id": api_key_id,  # user sub (stable)
            "owner_type": "user",
            "owner_id": owner_id,  # also sub (stable)
            "name": claims.get("email"),  # store minted client id
            "api_key": api_key,  # rotatable
            "keycloak_client_id": keycloak_client_id,  # MUST be minted client id
        }

        try:
            self._conn.execute(sql, params)
        except sqlite3.IntegrityError as e:
            raise ValueError(f"api_keys upsert failed: {e}") from e

    def hit_rate_limit_client(
        self,
        subject_id: str,
        *,
        limit: int = 1,
    ) -> Tuple[bool, int, int]:
        """
        Fixed-window rate limit per AZP. One request per minute
        """
        if not subject_id:
            raise ValueError("subject_id is required")

        # Compute the current minute bucket in SQLite's UTC "now" time.
        cur = self._conn.execute(
            "SELECT strftime('%Y-%m-%dT%H:%M:00Z','now') AS window_start"
        )
        window_start = cur.fetchone()["window_start"]

        # 1) Try to insert the row for this (subject_id, window_start).
        # 2) If it already exists, increment .

        self._conn.execute(
            """
            INSERT OR IGNORE INTO rate_limit_counters (
              subject_id, window_start, count
            ) VALUES (?, ?, 0)
            """,
            (subject_id, window_start),
        )

        self._conn.execute(
            """
            UPDATE rate_limit_counters
            SET count = count + 1
            WHERE subject_id = ? AND window_start = ?
            """,
            (subject_id, window_start),
        )

        cur = self._conn.execute(
            """
            SELECT count
            FROM rate_limit_counters
            WHERE subject_id = ? AND window_start = ?
            """,
            (subject_id, window_start),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("rate_limit_counters row missing after increment")

        new_count = int(row["count"])
        allowed = new_count <= limit

        now = int(time.time())

        retry_after = 0 if allowed else 60 - now % 60

        return allowed, retry_after, new_count
