import logging

from fastapi import APIRouter, Depends, Header, HTTPException

from app.db import AuthRepo, get_repo
from app.services.api_keys import parse_api_key
from app.services.keycloak import mint_validator
from app.utils import _sync_entitlements, decode_jwt_no_verify

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/mint")
def mint(
    authorization: str = Header(default="", alias="Authorization"),
    repo: AuthRepo = Depends(get_repo),
):
    try:
        client_id, client_secret = parse_api_key(authorization)
    except ValueError as err:
        raise HTTPException(status_code=401, detail=str(err)) from err

    try:
        token = mint_validator(client_id=client_id, client_secret=client_secret)
    except ValueError as err:
        raise HTTPException(
            status_code=401, detail="Invalid client credentials"
        ) from err
    except Exception as err:
        raise HTTPException(status_code=502, detail="Keycloak unavailable") from err

    claims = decode_jwt_no_verify(token["access_token"])
    apiKey = f"{client_id}:{client_secret}"

    repo.upsert_api_key_from_claims(claims, api_key=apiKey)

    row = repo.get_api_key_by_client_id(client_id)
    if row is None:
        raise HTTPException(status_code=500, detail="api_keys row missing after upsert")
    if row.status != "active":
        raise HTTPException(status_code=401, detail="API key is invalid or revoked")

    repo.touch_last_used(client_id)

    try:
        _sync_entitlements(claims=claims, api_key=apiKey, default_tier="free")
    except Exception as err:
        logger.warning("Entitlements sync failed: %s", err)

    return token
