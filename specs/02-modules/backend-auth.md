## Overview
- Auth token issuance and verification using JWT (HS256) for FastAPI routes (`backend/app/services/auth_service.py:12-48`, `backend/app/api/routes/auth.py:12-20`).
- OAuth2 password flow stub that accepts any username/password and returns a signed access token.

## Responsibilities & Non-Responsibilities
- Responsibilities: issue JWT access tokens; verify bearer tokens for protected routes; expose `/api/token` to obtain tokens.
- Non-Responsibilities: user credential storage/validation, refresh tokens, roles/permissions, token revocation/rotation, audit logging.

## Dependencies & Integration Points
- Settings: `auth_secret` from `Settings` (`backend/app/config.py:54`) used as HS256 secret; expiry minutes constant (`ACCESS_TOKEN_EXPIRE_MINUTES=30`).
- FastAPI OAuth2PasswordBearer is declared with `tokenUrl="/api/token"` (`backend/app/services/auth_service.py:16`).
- `verify_token` is injected as dependency in `app.main` when auth is enabled (see `backend-core` spec).
- External libs: `jose.jwt` for encode/decode; `pydantic.BaseModel` for `TokenData`.

## Interfaces & Contracts
- `POST /api/token` (`backend/app/api/routes/auth.py:12-20`): body via OAuth2PasswordRequestForm; returns `{"access_token": <jwt>, "token_type": "bearer"}`. Contract: no credential checks; accepts any username/password.
- `create_access_token(data: dict, expires_delta: timedelta|None)` (`backend/app/services/auth_service.py:23-31`): signs payload + `exp` claim; default expiry 15m when `expires_delta` absent.
- `verify_token(token=Depends(oauth2_scheme)) -> TokenData` (`backend/app/services/auth_service.py:34-48`): decodes JWT with HS256 secret; expects `sub` claim; raises 401 on failure.

## Data Models
- `TokenData {username?: str}` (`backend/app/services/auth_service.py:19-21`).
- JWT claims: arbitrary `data` plus `exp`; `sub` used as username identifier.

## Control Flows
- Token issuance: `/api/token` builds `expires_delta` (30m) → calls `create_access_token` with `{"sub": form_data.username}` → returns token.
- Verification: dependency decodes token, extracts `sub`, raises 401 if missing/invalid.

## Config & Runtime Parameters
- `auth_secret` env `CORTEX_AUTH_SECRET` controls signing/verification.
- `ACCESS_TOKEN_EXPIRE_MINUTES=30`; default expiry 15m if called without delta.
- Auth can be skipped via `Settings.debug` or `Settings.skip_auth` (see `backend-core` spec).

## Error & Failure Semantics
- Invalid/missing token → HTTP 401 with `WWW-Authenticate: Bearer`.
- No account lockout/brute-force protection; `/api/token` always succeeds with any credentials.
- No token revocation; secret rotation invalidates all tokens.

## Observability
- No logging/metrics for token issuance or verification.

## Risks, Gaps, and [ASSUMPTION] Blocks
- No credential validation; any username/password gets a token — security risk for non-test environments.
- Single static secret, no rotation/versioning. [ASSUMPTION] Production overrides secret and fronts service with real IdP.
- No scopes/roles; all authenticated users equivalent.
- Missing audit trail for token issuance and failed validations.

## Verification Ideas
- Add tests: token issuance returns 200 and token decodes with expected `sub` and `exp`; verify 401 for tampered/expired tokens.
- Integration: ensure auth dependency enforced when `skip_auth=False`; endpoints deny requests without Authorization header.
- Security hardening: integrate real user store/IdP; add secret rotation and revocation tests.
