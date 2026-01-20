import logging
import os

import requests

logger = logging.getLogger(__name__)
ENTITLEMENTS_BASE = os.getenv("ENTITLEMENTS_BASE", "http://127.0.0.1:8000")


def _sync_entitlements(
    *, claims: dict, api_key: str, default_tier: str = "free"
) -> None:
    payload = {
        "user_id": claims.get("sub"),
        "api_key": api_key,
        "account_name": (
            claims.get("user_email")
            or claims.get("api_key_owner")
            or claims.get("preferred_username")
            or "unknown"
        ),
        "default_tier": default_tier,
    }

    r = requests.post(
        f"{ENTITLEMENTS_BASE.rstrip('/')}/internal/subjects/sync",
        json=payload,
        timeout=3.0,
    )
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"entitlements sync failed: {r.status_code} {r.text}")
