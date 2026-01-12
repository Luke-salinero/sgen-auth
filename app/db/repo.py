from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal, Optional

OwnerType = Literal["user", "workspace"]
Status = Literal["active", "revoked"]


@dataclass(frozen=True)
class ApiKeyRow:
    id: str
    owner_type: OwnerType
    owner_id: str
    name: str
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
          id, owner_type, owner_id, name, keycloak_client_id, status,
          created_by_user_id, created_at, last_used_at, revoked_at
        FROM api_keys
        WHERE keycloak_client_id = ?
        LIMIT 1
        """
        cur = self._conn.execute(sql, (client_id,))
        row = cur.fetchone()
        return _row_to_api_key(row) if row else None

    def list_api_keys(self, owner_type: OwnerType, owner_id: str) -> list[ApiKeyRow]:
        sql = """
        SELECT
          id, owner_type, owner_id, name, keycloak_client_id, status,
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
        keycloak_client_id: str,
        created_by_user_id: Optional[str] = None,
    ) -> None:
        sql = """
        INSERT INTO api_keys (
          id, owner_type, owner_id, name, keycloak_client_id,
          status, created_by_user_id
        ) VALUES (?, ?, ?, ?, ?, 'active', ?)
        """
        self._conn.execute(
            sql,
            (
                key_id,
                owner_type,
                owner_id,
                name,
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
