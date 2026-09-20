# sgen-auth

Authentication and authorization service for the sgen platform.

This service is responsible for:
- Minting short-lived JWTs from an API key (`client_id:client_secret`) via Keycloak's client-credentials grant
- Self-service API key issuance/rotation for Keycloak-SSO-authenticated users, rate-limited per subject
- Provisioning the Keycloak confidential client + protocol mappers behind each API key
- Syncing newly-minted subjects into `sgen-entitlement`
- Emailing newly minted/rotated keys to the owning account

## Tech Stack
- Python
- FastAPI
- SQLite (local/dev)
- JWT
- Keycloak (OIDC)

## Repository Structure
```
sgen-auth/
├── app/
│   ├── api/v1/routes/
│   │   ├── mint.py        # POST /v1/mint
│   │   └── api_keys.py    # POST /v1/keys
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   ├── connection.py  # sqlite3 connection helper (used by init_db)
│   │   ├── dbConn.py      # FastAPI Depends: get_db / get_repo
│   │   ├── init_db.py     # runs app/db/schema.sql on startup
│   │   └── repo.py        # AuthRepo - all parameterized SQL lives here
│   ├── services/
│   │   ├── api_keys/
│   │   │   ├── generate_api_keys.py  # Keycloak client/secret provisioning
│   │   │   └── parser.py             # parses "ApiKey client_id:client_secret"
│   │   └── keycloak/
│   │       └── validator.py          # client_credentials grant against Keycloak
│   ├── utils/
│   │   ├── decode_jwt.py       # bearer-JWT verification (JWKS/RS256)
│   │   ├── sync_entitlement.py # POSTs new subjects to sgen-entitlement
│   │   └── send_email.py       # SMTP delivery of minted/rotated keys
│   └── main.py
├── requirements.txt
├── README.md
```

## Responsibilities
This service:
- Validates API keys and bearer JWTs
- Mints JWTs for validated API keys (`POST /v1/mint`)
- Issues/rotates API keys for authenticated Keycloak identities (`POST /v1/keys`)
- Integrates with Keycloak as the identity provider

## Setup

### Create and activate virtual environment
```bash
python -m venv .venv
```

Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Running the Service
```bash
uvicorn app.main:app --reload
```

Service will be available at:
- http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

## Configuration
Configuration is managed via environment variables and `app/core/config.py`.

Example:
```env
ENV=dev
DEBUG=1
JWT_ISSUER=sgen
JWT_AUDIENCE=sgen-api
DB_PATH=app/data/auth.db
```

## Database
- SQLite is used for local development; all access goes through `AuthRepo` (`app/db/repo.py`) with parameterized queries.
- `init_db()` (`app/db/init_db.py`) runs on every startup and expects `app/db/schema.sql` to exist — **that file is not currently checked into this repo**, so a clean clone/deploy will fail at startup until it's added or `init_db()` is changed to create the schema another way.

## API Overview
| Method | Path | Description |
| ------ | ---- | ----------- |
| `POST` | `/v1/mint` | Exchanges an API key (`Authorization: ApiKey client_id:client_secret`) for a JWT via Keycloak's client-credentials grant. |
| `POST` | `/v1/keys` | Mints or rotates the caller's API key (`Authorization: Bearer <JWT>`, Keycloak SSO). Rate-limited to 1 request/minute per subject; emails the key to the caller's `email` claim. |

## Development Notes
- Business logic is kept out of route handlers
- Keycloak validation is isolated in `services/keycloak`

## Security Notes
- Secrets and private keys must never be committed
- JWT validation is enforced server-side (audience + issuer + signature, via JWKS)
- `KEYCLOAK_ADMIN_PASSWORD` has no default; it must be set explicitly for `/v1/keys` to be able to provision Keycloak clients

