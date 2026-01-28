Jan 25, 2026 — API Keys & Auth Integration

-Added api_keys.py with a /v1/keys endpoint to accept website requests authenticated via Bearer JWT.
-Updated generate_api_keys.py to generate deterministic, UUID-based client IDs for API keys.
-Refactored decode_jwt to reuse verify_jwt logic from the Entitlement service.
-Updated configuration to source JWT settings directly from the Entitlement repository.
Open questions:
?-How to prevent exposing Keycloak connection details to the frontend while still supporting Bearer-token–based API key creation.
?-Whether API keys should be persisted immediately upon creation or only recorded on first use.

Jan 28, 2026 — API Keys & Auth Integration

-Added schema table for minute-bucketed rate limiting
-Enforced per-subject (sub) rate limiting on API key requests
-Initialized database schema during app startup
-Added repo method to track and enforce request counts
-Updated API key upsert to support subject-based overrides
TODO - Clarified and normalized usage of subject_id vs client_id vs user_id