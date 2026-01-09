import os

import requests

VALIDATOR_BASE = os.getenv("VALIDATOR_BASE", "http://127.0.0.1:9100")


def mint_via_validator(*, client_id: str, client_secret: str) -> dict:
    r = requests.post(
        f"{VALIDATOR_BASE}/internal/mint",
        json={"client_id": client_id, "client_secret": client_secret},
        timeout=15,
    )

    if r.status_code != 200:
        # keep it simple: treat any non-200 as invalid for now
        raise ValueError(r.text)

    return r.json()
