from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.api_keys import KeycloakApiError, generate_api_key_if_missing
from app.utils import AuthenticationError, authenticate_request, send_email

router = APIRouter()


class ApiKeyRequest(BaseModel):
    rotate: bool = False
    email_key: bool = True


@router.post("/keys")
def api_keys(req: ApiKeyRequest, request: Request):
    try:
        ident = authenticate_request(request.headers)
        claims = ident.raw_claims

        email = claims.get("email")
        if not email:
            raise HTTPException(400, "Token missing email claim")

        username = ident.subject_id
        res = generate_api_key_if_missing(
            username=username,
            email=email,
            rotate_secret=req.rotate,
        )

        if req.email_key:
            subject = "New SGEN API Key" if req.rotate else "SGEN API Key"
            body = f"Here is your SGEN API key:\n\n{res.api_key}\n\n"
            if req.rotate:
                body += (
                    "This key was rotated. Your previous API key is now invalid.\n\n"
                )
            send_email(to=email, subject=subject, body=body)

        return {"client_id": res.client_id, "rotated": req.rotate}
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message) from e
    except KeycloakApiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
