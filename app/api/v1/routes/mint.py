from fastapi import APIRouter, Header, HTTPException

from app.services.api_keys.parser import parse_api_key
from app.services.validator.client import mint_validator

router = APIRouter()


@router.post("/mint")
def mint(authorization: str = Header(default="")):
    try:
        client_id, client_secret = parse_api_key(authorization)
    except ValueError as err:
        raise HTTPException(status_code=401, detail=str(err)) from err

    try:
        return mint_validator(client_id=client_id, client_secret=client_secret)
    except ValueError as err:
        raise HTTPException(status_code=401, detail=str(err)) from err
