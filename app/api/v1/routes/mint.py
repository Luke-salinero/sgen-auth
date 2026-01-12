from fastapi import APIRouter, Depends, Header, HTTPException

from app.db import AuthRepo, get_repo
from app.services.api_keys import parse_api_key
from app.services.keycloak import mint_validator

router = APIRouter()


@router.post("/mint")
def mint(
    authorization: str = Header(default="", alias="Authorization"),
    repo: AuthRepo = Depends(get_repo),
):
    try:
        client_id, client_secret = parse_api_key(authorization)
    except ValueError as err:
        raise HTTPException(status_code=401, detail=str(err)) from err

    row = repo.get_api_key_by_client_id(client_id)
    if row is None or row.status != "active":
        raise HTTPException(status_code=401, detail="API key is invalid or revoked")

    try:
        token = mint_validator(client_id=client_id, client_secret=client_secret)
    except ValueError as err:
        # Keycloak rejected credentials
        raise HTTPException(
            status_code=401, detail="Invalid client credentials"
        ) from err
    except Exception as err:
        # Keycloak is down / network error
        raise HTTPException(status_code=502, detail="Keycloak unavailable") from err

    repo.touch_last_used(client_id)
    return token
