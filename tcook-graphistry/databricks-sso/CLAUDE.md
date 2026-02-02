# Databricks SSO Project Context

## Overview

This project configures Okta SSO for Graphistry, supporting both the Graphistry web UI
and the pygraphistry Python client running in Databricks notebooks.

## Architecture

Two components are involved in the SSO flow:

1. **Graphistry Nexus (server)** — Django web app at `graphistry-nexus-copy/`
   - Handles OIDC authentication with identity providers
   - Default OIDC flow: **PKCE** (`FLOW_PKCE` in `nexus/allauth_ext/socialaccount/providers/openid_connect/provider.py:35`)
   - Supports FLOW_NO_PKCE as a fallback for providers like Keycloak
   - Okta provider template in `common/sso_provider_configs.py` uses endpoints:
     `/oauth2/v1/authorize`, `/oauth2/v1/token`, `/oauth2/v1/userinfo`

2. **pygraphistry (client)** — Python SDK at `pygraphistry/`
   - Does NOT perform PKCE itself; the Nexus server handles the OIDC exchange
   - Client flow: POST to `/api/v2/g/sso/oidc/login/` → gets `state` + `auth_url` →
     user clicks link → polls `/api/v2/o/sso/oidc/jwt/{state}/` for JWT
   - Databricks branch: `dbricks-sso-register` (commits by tcook and vaimdev)
   - Added `databricks_notebook_sso_login()` for displaying HTML login links in notebooks

## Okta App Configuration

**Okta app type must be SPA (Single-Page Application)**, not Web App.

Reasons:
- Nexus server uses PKCE by default (no client_secret in token exchange)
- SSO Admin Guide explicitly states: Okta Application Type = SPA
- Admin guide: https://graphistry-admin-docs.readthedocs.io/en/latest/security/SSO.html

Key settings for the Okta SPA app:
- `application_type`: `browser` (Okta API value for SPA)
- `token_endpoint_auth_method`: `none` (PKCE, no secret)
- `grant_types`: `authorization_code` only
- `response_types`: `code`
- `pkce_code_challenge_method`: `S256`

## Callback URLs

- Site-wide SSO: `https://{server}/g/sso/oidc/{idp_name}/login/callback/`
- Org-level SSO: `https://{server}/o/{org_id}/sso/oidc/{idp_name}/login/callback/`
- Logout: `https://{server}/accounts/logout/`

## Databricks Notebook Usage

```python
import graphistry

# For dbricks-sso-register branch (has databricks_notebook_sso_login):
graphistry.databricks_notebook_sso_login(
    server="graphistry-dev.grph.xyz", protocol="https", api=3,
    org_name=None, idp_name=None, is_sso_login=True,
    sso_opt_into_type="display"
)

# Standard register (works on master):
graphistry.register(
    api=3, protocol="https", server="graphistry-dev.grph.xyz",
    is_sso_login=True, sso_opt_into_type="display"
)
```

## Supported Identity Providers

| Provider | PKCE | App Type | Notes |
|----------|------|----------|-------|
| Okta | Yes | SPA | Default; uses `/oauth2/v1/` endpoints |
| Auth0 | Yes | SPA | Supports native org feature |
| Keycloak | No | Confidential | Uses `client_secret`; `FLOW_NO_PKCE` |
| Entra ID | Yes | SPA | Needs `Origin` header; uses tenant_id |
| ADFS | Varies | Confidential | SSL verify disabled (self-signed certs) |

## Key Files

- `okta/okta_create_graphistry_spa.sh` — Current correct script (SPA + PKCE)
- `okta/old_scripts/okta_create_graphistry_app.sh` — Deprecated (Web App + client_secret)
- `databricks_graphistry_sso_test.py` — Test notebook for Databricks SSO
- `graphistry-nexus-copy/common/sso_provider_configs.py` — Provider endpoint templates
- `graphistry-nexus-copy/nexus/allauth_ext/socialaccount/providers/openid_connect/client.py` — PKCE implementation
- `pygraphistry/graphistry/pygraphistry.py` — Client SSO logic
- `pygraphistry/graphistry/arrow_uploader.py` — Low-level OIDC API calls

## pygraphistry SSO Branches

- `dbricks-sso-register` — Databricks HTML login link + notebook UX (tcook + vaimdev)
- `dbricks-sso-2` — Stdout flushing experiments for timer display
- `dev/sso_login_ux` — SSO login UX improvements (vaimdev)
- `fix/refresh_sso` — SSO token refresh fixes
- `org_sso_login` — Org-scoped SSO login

## Building Graphistry from Source

The `graphistry/` directory is a shallow clone of `git@github.com:graphistry/graphistry.git`.
Builds use Docker Compose with BuildKit. All commands run from the `graphistry/` directory.

### Prerequisites

- Docker 19.03+ with BuildKit
- Docker Compose v2+
- Make

### Build base images (sequential — each depends on the previous)

```bash
cd graphistry/
make base_native svc=05-nvidia       # RAPIDS, Python, CUDA/cuDNN
make base_native svc=40-node         # Node.js, TypeScript, yarn
make base_native svc=50-deps         # Python packages, system libs, JS compilation
make base_native svc=60-base         # Graphistry base application layer
make base_native svc=63-forge-base   # Forge ETL base
```

Or all at once: `make base_native_all`

### Build application images (15 services)

```bash
make app_native_all
```

This builds: graph-app-kit-public, graph-app-kit-private, streamgl-viz, streamgl-gpu,
streamgl-sessions, pivot, forge-etl-python, dask-scheduler, dask-cuda-worker, nexus,
notebook, redis, postgres, nginx, caddy.

To build a single app service: `make app_native svc=nexus`

### Image tags

Images are tagged as `graphistry/<service>:v<VERSION>-<CUDA_SHORT_VERSION>`.
Version is read from `versions/VERSION`. Infrastructure services (redis, postgres, caddy)
use the `-universal` suffix.

### Full build (base + app)

```bash
make base_native_all && make app_native_all
```

## Changes Made (Jan 2026)

### P0 Fix: Redis cache for PKCE code verifier

**File:** `graphistry/apps/core/nexus/config/settings/base.py:900`

Changed Django `CACHES['default']` from `LocMemCache` to `django_redis.cache.RedisCache`.

**Problem:** The PKCE flow stores a code verifier in Django's cache (`sso_cv_{state}`) during the authorize step and retrieves it during the callback. With `LocMemCache`, each Gunicorn worker has its own process-local cache. If different workers handle the authorize and callback requests, the verifier is lost, and Okta returns "Code verifier required."

**Fix:** Use Redis (already configured as a secondary cache alias) as the default backend so all workers share the same cache store.

### SSO Diagnostic Tooling

**Files added:**
- `notebooks/diagnose_sso.py` — Standalone diagnostic script (CLI + importable API). Runs 9 client-side checks: server reachability, SSO endpoint, PKCE params, client_id, redirect_uri, scopes, response_type, IdP reachability, token poll. Generates server-side hints for known issues. Supports `--json` output.
- `notebooks/databricks_sso_runbook.ipynb` — Interactive Databricks notebook (11 cells). Step-by-step SSO login and validation using non-blocking `sso_timeout=None`. Includes inline diagnostics, token verification, smoke test graph plot, and token refresh test (validates the P0 bug scenario).

### SSO Error Reproduction Tooling

**Files added:**
- `notebooks/reproduce_sso_errors.py` — Standalone script to reproduce the three client errors (Livia Hull, Jan 27-28 2026). CLI with `--test error1|error2|error3|fixed` flags. Error 1 tests PKCE cache miss, Error 2 tests polling race, Error 3 tests wrong API call, fixed tests non-blocking flow.
- `notebooks/reproduce_sso_errors.ipynb` — Databricks notebook version (10 cells). Each error has its own cell with HTML output. Includes the fixed flow (Cells 7-8) for validating the correct non-blocking pattern.

### Test Results (Feb 2 2026)

**Diagnostic (`diagnose_sso.py`) — graphistry-dev.grph.xyz:**
- 9/9 checks passed (server, SSO endpoint, PKCE S256, client_id, redirect_uri, scopes, response_type, IdP reachable, token poll)

**Diagnostic (`diagnose_sso.py`) — localhost (local build v2.45.11):**
- 9/9 checks passed after Okta SSO provider configured
- Okta SPA app: `client_id=0oaxrffajvUZ...`, IdP: `integrator-7669542.okta.com`
- Provider name: `Okta_Site_wide`

**Error reproduction (`reproduce_sso_errors.py`) — localhost:**
- Error 2 (P1) "State is invalid": REPRODUCED — polling race confirmed, times out after 15s
- Error 3 (P2) login() TypeError: REPRODUCED — `graphistry.login()` without args raises TypeError
- Error 1 (P0) "Code verifier required": Requires LocMemCache to reproduce; with Redis fix applied, SSO callback should succeed
- Fixed flow: Requires interactive browser login (run manually in terminal)
