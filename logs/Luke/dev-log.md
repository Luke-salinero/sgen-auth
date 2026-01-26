Jan 25, 2026 — API Keys & Auth Integration
-Added api_keys.py with a /v1/keys endpoint to accept website requests authenticated via Bearer JWT.
-Updated generate_api_keys.py to generate deterministic, UUID-based client IDs for API keys.
-Refactored decode_jwt to reuse verify_jwt logic from the Entitlement service.
-Updated configuration to source JWT settings directly from the Entitlement repository.
Open questions:
?-How to prevent exposing Keycloak connection details to the frontend while still supporting Bearer-token–based API key creation.
?-Whether API keys should be persisted immediately upon creation or only recorded on first use.