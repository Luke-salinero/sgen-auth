from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.db import AuthRepo, get_repo
from app.services.api_keys import KeycloakApiError, generate_api_key_if_missing
from app.utils import AuthenticationError, authenticate_request, send_email

router = APIRouter()


class ApiKeyRequest(BaseModel):
    rotate: bool = False
    email_key: bool = True


@router.post("/keys")
def api_keys(req: ApiKeyRequest, request: Request, repo: AuthRepo = Depends(get_repo)):
    try:
        ident = authenticate_request(request.headers)
        claims = ident.raw_claims

        user_sub = claims.get("sub")
        if not user_sub:
            raise HTTPException(status_code=400, detail="Token missing sub")

        # Rate limit per user (sub): 1 request/minute
        allowed, retry_after, _count = repo.hit_rate_limit_client(user_sub, limit=1)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

        email = claims.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Token missing email claim")

        if not req.rotate:
            existing = repo.get_api_key_by_sub(user_sub)
            if existing is not None and existing.status == "active":
                if req.email_key:
                    subject = "SGEN API Key"
                    body = f"Here is your SGEN API key:\n\n{existing.api_key}\n\n"
                    send_email(to=email, subject=subject, body=body)
                return {"client_id": existing.keycloak_client_id, "rotated": False}

        # Mint or rotate in Keycloak
        res = generate_api_key_if_missing(
            username=user_sub,  # stored as api_key_owner
            email=email,
            rotate_secret=req.rotate,
        )

        # Persist in DB keyed on the minted client id
        repo.upsert_api_key_from_claims(
            claims,
            api_key=res.api_key,
            keycloak_client_id_override=res.client_id,
        )

        row = repo.get_api_key_by_client_id(res.client_id)
        if row is None:
            raise HTTPException(status_code=500, detail="api_keys missing after upsert")
        if row.status != "active":
            raise HTTPException(status_code=401, detail="API key is invalid or revoked")

        repo.touch_last_used(res.client_id)

        if req.email_key:
            subject = "New SGEN API Key" if req.rotate else "SGEN API Key"
            body = f"Here is your SGEN API key:\n\n{res.api_key}\n\n"
            if req.rotate:
                body += "This key was rotated. The previous API key is now invalid.\n\n"
            send_email(to=email, subject=subject, body=body)

        return {"client_id": res.client_id, "rotated": req.rotate}

    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message) from e
    except KeycloakApiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
