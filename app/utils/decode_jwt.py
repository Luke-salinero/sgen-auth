import base64
import json
from typing import Any


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def decode_jwt_no_verify(jwt: str) -> dict[str, Any]:
    """
    Decodes JWT payload without verifying signature.
    Assumes standard JWS format: header.payload.signature
    """
    parts = jwt.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format (expected 3 parts)")

    payload_b64 = parts[1]
    payload_json = _b64url_decode(payload_b64).decode("utf-8")
    return json.loads(payload_json)
