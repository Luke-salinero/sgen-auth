def parse_api_key(authz: str) -> tuple[str, str]:
    # Authorization: ApiKey client_id:client_secret
    if not authz.startswith("ApiKey "):
        raise ValueError("Expected Authorization: ApiKey <client_id>:<client_secret>")

    raw = authz[len("ApiKey ") :].strip()
    if ":" not in raw:
        raise ValueError("API key must be <client_id>:<client_secret>")

    client_id, client_secret = raw.split(":", 1)
    if not client_id or not client_secret:
        raise ValueError("Invalid API key format")

    return client_id, client_secret
