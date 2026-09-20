from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ApiKeyResult:
    client_id: str
    client_uuid: str
    client_secret: str
    api_key: str  # client_id:client_secret


class KeycloakApiError(RuntimeError):
    pass


def _die(msg: str) -> None:
    raise KeycloakApiError(msg)


def stable_client_id(prefix: str, email: str, length: int = 10) -> str:
    get_namespace = os.getenv("UUID_NAMESPACE")
    namespace = uuid.UUID(get_namespace)
    norm = email.strip().lower()
    u = uuid.uuid5(namespace, norm)
    return f"{prefix}-{u.hex[:length]}"


def get_admin_token(keycloak_base: str, admin_user: str, admin_pass: str) -> str:
    token_url = f"{keycloak_base}/realms/master/protocol/openid-connect/token"
    r = requests.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": admin_user,
            "password": admin_pass,
        },
        timeout=15,
    )
    if r.status_code != 200:
        _die(f"Failed to get admin token ({r.status_code}): {r.text}")
    return r.json()["access_token"]


def create_client_if_missing(
    keycloak_base: str, realm: str, token: str, client_id: str
) -> None:
    url = f"{keycloak_base}/admin/realms/{realm}/clients"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "clientId": client_id,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,  # confidential client
        "serviceAccountsEnabled": True,  # enables client_credentials
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "implicitFlowEnabled": False,
    }

    r = requests.post(url, json=payload, headers=headers, timeout=15)
    if r.status_code in (201, 204, 409):
        return
    _die(f"Failed to create client ({r.status_code}): {r.text}")


def get_client_rep(
    keycloak_base: str, realm: str, token: str, client_id: str
) -> Optional(Dict[str, Any]):
    url = f"{keycloak_base}/admin/realms/{realm}/clients"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params={"clientId": client_id}, headers=headers, timeout=15)
    if r.status_code != 200:
        _die(f"Failed to lookup client ({r.status_code}): {r.text}")
    data = r.json()
    for c in data:
        if c.get("clientId") == client_id and c.get("id"):
            return c
    return None


def get_client_secret(
    keycloak_base: str, realm: str, token: str, client_uuid: str
) -> str:
    url_prefix = f"{keycloak_base}/admin/realms/{realm}"
    url = url_prefix + f"/clients/{client_uuid}/client-secret"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        _die(f"Failed to get secret ({r.status_code}): {r.text}")
    secret = r.json().get("value")
    if not secret:
        _die(f"No secret 'value' in response: {r.text}")
    return secret


def rotate_client_secret(
    keycloak_base: str, realm: str, token: str, client_uuid: str
) -> str:
    url_prefix = f"{keycloak_base}/admin/realms/{realm}"
    url = url_prefix + f"/clients/{client_uuid}/client-secret"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(url, headers=headers, timeout=15)
    if r.status_code != 200:
        _die(f"Failed to rotate secret ({r.status_code}): {r.text}")
    secret = r.json().get("value")
    if not secret:
        _die(f"No secret 'value' in response: {r.text}")
    return secret


def get_service_account_user(
    keycloak_base: str, realm: str, token: str, client_uuid: str
) -> Dict[str, Any]:
    url_prefix = f"{keycloak_base}/admin/realms/{realm}"
    url = url_prefix + f"/clients/{client_uuid}/service-account-user"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        _die(f"Failed to get service account user ({r.status_code}): {r.text}")
    return r.json()


def update_user_attributes_bulk(
    keycloak_base: str,
    realm: str,
    token: str,
    user_id: str,
    attributes: Dict[str, str],
) -> None:
    url = f"{keycloak_base}/admin/realms/{realm}/users/{user_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    r0 = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    if r0.status_code != 200:
        _die(f"Failed to read user rep ({r0.status_code}): {r0.text}")
    rep = r0.json()

    attrs = rep.get("attributes") or {}
    for k, v in attributes.items():
        attrs[k] = [v]
    rep["attributes"] = attrs

    # Currently gives "User already has that email" error. Come back and look
    # ways to combat this -----
    # if "email" in attributes:
    #     rep["email"] = attributes["email"]
    #     rep["emailVerified"] = True

    r = requests.put(url, headers=headers, json=rep, timeout=15)
    if r.status_code != 204:
        _die(f"Failed to update user attributes ({r.status_code}): {r.text}")


def list_protocol_mappers(
    keycloak_base: str, realm: str, token: str, client_uuid: str
) -> list[Dict[str, Any]]:
    url_prefix = f"{keycloak_base}/admin/realms/{realm}/clients"
    url = url_prefix + f"/{client_uuid}/protocol-mappers/models"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        _die(f"Failed to list protocol mappers ({r.status_code}): {r.text}")
    return r.json()


def create_protocol_mapper(
    keycloak_base: str, realm: str, token: str, client_uuid: str, mapper: Dict[str, Any]
) -> None:
    url_prefix = f"{keycloak_base}/admin/realms/{realm}/clients"
    url = url_prefix + f"/{client_uuid}/protocol-mappers/models"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url, json=mapper, headers=headers, timeout=15)
    if r.status_code not in (201, 204):
        _die(f"Failed to create protocol mapper ({r.status_code}): {r.text}")


def update_protocol_mapper(
    keycloak_base: str,
    realm: str,
    token: str,
    client_uuid: str,
    mapper_id: str,
    mapper: Dict[str, Any],
) -> None:
    url_prefix = f"{keycloak_base}/admin/realms/{realm}/clients"
    url = url_prefix + f"/{client_uuid}/protocol-mappers/models/{mapper_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.put(url, json=mapper, headers=headers, timeout=15)
    if r.status_code != 204:
        _die(f"Failed to update protocol mapper ({r.status_code}): {r.text}")


def ensure_user_attribute_mapper(
    keycloak_base: str,
    realm: str,
    token: str,
    client_uuid: str,
    *,
    user_attr: str,
    claim_name: str,
    mapper_name: str,
) -> None:
    existing = list_protocol_mappers(keycloak_base, realm, token, client_uuid)
    found: Optional[Dict[str, Any]] = None
    for m in existing:
        if m.get("name") == mapper_name:
            found = m
            break

    desired = {
        "name": mapper_name,
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "consentRequired": False,
        "config": {
            "user.attribute": user_attr,
            "claim.name": claim_name,
            "jsonType.label": "String",
            "access.token.claim": "true",
            "id.token.claim": "false",
            "userinfo.token.claim": "true",
            "aggregate.attrs": "false",
            "multivalued": "false",
        },
    }

    if found is None:
        create_protocol_mapper(keycloak_base, realm, token, client_uuid, desired)
        return

    found_id = found.get("id")
    if not found_id:
        _die("Existing mapper had no 'id' field; cannot update it.")

    cfg = found.get("config") or {}
    if cfg.get("user.attribute") == user_attr and cfg.get("claim.name") == claim_name:
        return

    desired_with_id = dict(desired)
    desired_with_id["id"] = found_id
    update_protocol_mapper(
        keycloak_base, realm, token, client_uuid, found_id, desired_with_id
    )


def generate_api_key_if_missing(
    *, username: str, email: str, rotate_secret: bool
) -> ApiKeyResult:
    """
    Idempotent behavior:
      - Uses a stable clientId derived from username.
      - If client already exists, we DO NOT rotate by default.
      - We still ensure attributes + mappers are correct.
    """
    keycloak_base = os.getenv("KEYCLOAK_BASE", "http://127.0.0.1:8080").rstrip("/")
    realm = os.getenv("KEYCLOAK_REALM", "sgen-test")
    admin_user = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
    admin_pass = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
    if not admin_pass:
        _die("KEYCLOAK_ADMIN_PASSWORD is not set")
    if not username.strip():
        _die("username is required")
    if not email.strip():
        _die("email is required")

    prefix = "sgen-api"
    client_id = stable_client_id(prefix=prefix, email=email, length=7)

    token = get_admin_token(keycloak_base, admin_user, admin_pass)

    # 1) Ensure client exists
    create_client_if_missing(keycloak_base, realm, token, client_id)
    client_rep = get_client_rep(keycloak_base, realm, token, client_id)
    if not client_rep:
        _die(f"Client {client_id} not found after create.")

    client_uuid = client_rep["id"]

    # 2) Ensure service-account user attributes are set
    svc_user = get_service_account_user(keycloak_base, realm, token, client_uuid)
    svc_user_id = svc_user.get("id")
    if not svc_user_id:
        _die("Service account user had no id.")
    attrs_to_set = {"api_key_owner": username, "api_key_email": email}
    update_user_attributes_bulk(keycloak_base, realm, token, svc_user_id, attrs_to_set)

    # 3) Ensure mappers exist for api_key_owner + email
    ensure_user_attribute_mapper(
        keycloak_base,
        realm,
        token,
        client_uuid,
        user_attr="api_key_owner",
        claim_name="api_key_owner",
        mapper_name="usermodel-api-key-owner",
    )
    ensure_user_attribute_mapper(
        keycloak_base,
        realm,
        token,
        client_uuid,
        user_attr="api_key_email",
        claim_name="api_key_email",
        mapper_name="usermodel-api-key-email",
    )
    # 4) Secret
    if rotate_secret:
        secret = rotate_client_secret(keycloak_base, realm, token, client_uuid)
    else:
        secret = get_client_secret(keycloak_base, realm, token, client_uuid)

    api_key = f"{client_id}:{secret}"
    return ApiKeyResult(
        client_id=client_id,
        client_uuid=client_uuid,
        client_secret=secret,
        api_key=api_key,
    )
