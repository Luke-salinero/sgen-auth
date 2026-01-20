# sgen-auth

Authentication and authorization service for the sgen platform.

This service is responsible for:
- Issuing and validating JWTs
- API key parsing and validation
- Integrating with Keycloak for identity verification
- Resolving and syncing entitlement data
- Providing authentication-related API endpoints

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
│   ├── api/
│   │   └── v1/
│   │       └── routes/
│   │           └── mint.py
│   ├── core/
│   │   └── config.py
│   ├── data/
│   │   └── auth.db
│   ├── db/
│   │   ├── connection.py
│   │   ├── dbConn.py
│   │   ├── repo.py
│   │   └── schema.sql
│   ├── services/
│   │   ├── api_keys/
│   │   │   └── parser.py
│   │   └── keycloak/
│   │       └── validator.py
│   ├── utils/
│   │   ├── decode_jwt.py
│   │   ├── sync_entitlements.py
│   │   └── time.py
│   └── main.py
├── requirements.txt
├── README.md
```

## Responsibilities
This service:
- Authenticates incoming requests
- Validates JWTs and API keys
- Mints JWTs for authenticated identities
- Integrates external identity providers (Keycloak)

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
- SQLite is used for local development
- Schema is defined in `app/db/schema.sql`

## API Overview
- POST /api/v1/mint — Issues a JWT for a validated identity

## Development Notes
- Business logic is kept out of route handlers
- Keycloak validation is isolated in `services/keycloak`

## Security Notes
- Secrets and private keys must never be committed
- JWT validation is enforced server-side

