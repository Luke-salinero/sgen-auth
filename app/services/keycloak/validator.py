import os

import requests

KEYCLOAK_BASE = os.getenv("KEYCLOAK_BASE", "http://127.0.0.1:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "sgen-test")


def mint_validator(*, client_id: str, client_secret: str) -> dict:
    token_url = f"{KEYCLOAK_BASE}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"

    r = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )

    try:
        body = r.json()
    except Exception:
        body = {"error": "non_json_response", "raw": r.text}

    if r.status_code != 200:
        # treat any Keycloak failure as invalid credentials for now
        raise ValueError(body)

    return body
