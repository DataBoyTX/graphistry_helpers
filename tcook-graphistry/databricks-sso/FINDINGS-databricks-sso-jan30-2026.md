# Databricks SSO Investigation — Jan 30, 2026

## TL;DR

Client (UK Dept for Business & Trade) is getting **"Code verifier required"** errors
when using pygraphistry SSO from Databricks notebooks. The root cause is likely the
Graphistry server losing the PKCE `code_verifier` from its Django cache between the
authorize request and the callback. A secondary issue is the client using a blocking
SSO timeout pattern that races against the login flow.

---

## Client Info

- **User:** L. Hull (`l*****@trade.gov.uk`), Senior Analytical Data Scientist, GSCIP
- **Org:** Department for Business & Trade (UK)
- **Contacts:** D. Hutchinson, J. Moore, K. Sibley, R. Turner, M. Early
- **Servers:**
  - `graphistry-pilot.atlas-lion.altana.ai` (org-level SSO, `org_name='gsci-pilot'`)
  - `graphistry-dev.grph.xyz` (site-wide SSO, used in our testing)
- **Okta domain:** `integrator-*****.okta.com` (auth URLs reference `sso.*****.gov.uk`)
- **Client ID:** `0oaxr*****vGl697`
- **Environment:** Databricks, Python 3.10

## Timeline

| Date | Event |
|------|-------|
| May 2024 | We sent working test notebook (`pygraphistry 0.33.8`, `test-v2-40-60.grph.xyz`, `org_name='louiedev'`, `sso_timeout=None`). **Worked.** |
| Jan 27, 2026 | Client reports: "I used Graphistry before, and it worked fine. This morning I seem to log in OK but I cannot actually see the graph." Server was upgraded, graphistry library updated. |
| Jan 27, 2026 | Client contact asks them to `pip install graphistry==0.44.1` (previously working version). Tested 0.50.5, 0.50.6, and 0.44.1. |
| Jan 27, 2026 | Client reports: "I've restarted the clusters in Databricks and there is definitely a login issue now." Shows "Code verifier required" error. |
| Jan 28, 2026 | Client demos error. Shows `graphistry.login()` TypeError and "Code verifier required" SSO Login Failure page. |
| Jan 29, 2026 | Graphistry (us) responds, asks for `%pip show graphistry` output, escalates to engineering. |
| Jan 30, 2026 | Client confirms: installed 0.50.6, SSO browser login works (screenshot shows successful login page), but plotting triggers re-auth and fails with "Code verifier required." |

## Errors Observed

### Error 1: "Code verifier required" (P0 — server-side)

```
SSO Login Failure
An error occurred while attempting to login via your SSO account.
Code: unknown, Error: Error retrieving access token:
b'{"error": "invalid_request", "error_description": "Code verifier required."}'
```

**Where it happens:** After the user successfully authenticates with Okta in the browser,
Okta redirects back to the Graphistry server with an authorization code. The server
then attempts to exchange that code for tokens at Okta's `/oauth2/v1/token` endpoint.
Okta rejects because the server didn't include the `code_verifier` in the request.

**Why:** The Nexus server uses PKCE (`FLOW_PKCE`). During the authorize step, it:
1. Generates a `code_verifier` and computes `code_challenge` (S256)
2. Stores the verifier in Django cache as `sso_cv_{state}`
3. Sends `code_challenge` to Okta in the auth URL

On callback, it retrieves the verifier from cache. If the cache entry is gone
(wrong backend, process mismatch, eviction, restart), the verifier is lost.

**Evidence:** The auth URLs in the notebook output confirm PKCE is active:
```
code_challenge=QxHxc*****xl0g
code_challenge_method=S256
```

**Likely cause:** Django `CACHES` backend on the server. If using `LocMemCache` (default,
per-process), the verifier stored by one worker won't be visible to another worker
handling the callback. Must use Redis or Memcached.

### Error 2: "State is invalid" (P1 — timing)

```
Exception: State is invalid
```

At `arrow_uploader.py:418` in `sso_get_token()`. The client's code polls
`/api/v2/o/sso/oidc/jwt/{state}/` and the server says the state doesn't exist.

**Why:** The client uses default `sso_timeout=50` (blocking mode) which starts polling
immediately. If the user hasn't completed the SSO flow in 50 seconds, or the
server-side OIDC exchange failed (see Error 1), the state is never fulfilled.

**Fix:** Use `sso_timeout=None` (non-blocking) as in the working May 2024 notebook.

### Error 3: `login()` missing arguments (P2 — client code)

```
TypeError: GraphistryClient.login() missing 2 required positional arguments:
'username' and 'password'
```

The client's `do_login()` function (from our May 2024 example) calls `graphistry.login()`
in a code path. In 0.50.6, `login()` is an instance method requiring username/password.
The function should call `sso_login()` or `register(is_sso_login=True)` instead.

## Architecture Overview

### Two components in the SSO flow

```
Databricks Notebook                  Graphistry Nexus Server              Okta
─────────────────                    ──────────────────────              ────
1. register(is_sso_login=True)
   └─► POST /api/v2/g/sso/oidc/login/
       ◄── {state, auth_url}         2. Generate code_verifier
                                        Store in cache: sso_cv_{state}
                                        Build auth_url with code_challenge
3. Display HTML link in notebook
   User clicks link ──────────────────────────────────────────────────► 4. Okta login page
                                                                        User authenticates
                                     5. Callback with auth code  ◄───── Okta redirects
                                        Retrieve code_verifier from cache
                                        Exchange code + verifier at Okta
                                        *** FAILS HERE: verifier missing ***
                                        Store JWT in session

6. Poll /api/v2/o/sso/oidc/jwt/{state}/
   ◄── JWT token (if successful)
```

### Key code locations

| Component | File | What |
|-----------|------|------|
| **Nexus PKCE** | `graphistry-nexus-copy/nexus/allauth_ext/socialaccount/providers/openid_connect/client.py` | Generates verifier (line 77), stores in cache (line 56), retrieves on callback (line 121) |
| **Nexus provider** | `graphistry-nexus-copy/nexus/allauth_ext/socialaccount/providers/openid_connect/provider.py:35` | `FLOW_PKCE` is the default |
| **Nexus Okta config** | `graphistry-nexus-copy/common/sso_provider_configs.py` | Okta endpoint templates |
| **pygraphistry SSO** | `pygraphistry/graphistry/pygraphistry.py` | `sso_login()`, `_handle_auth_url()`, `sso_get_token()` |
| **pygraphistry API** | `pygraphistry/graphistry/arrow_uploader.py` | `sso_login()` (POST), `sso_get_token()` (GET jwt) |
| **Databricks detection** | `pygraphistry/graphistry/util.py:225` | `in_databricks()` checks `DATABRICKS_RUNTIME_VERSION` |

## What Worked Before (May 2024)

- pygraphistry **0.33.8**
- Server: `test-v2-40-60.grph.xyz`
- Okta: `dev-*****.okta.com`, client_id `0oabe*****5d7`
- Org-level SSO: `org_name='louiedev'`
- **`sso_timeout=None`** (non-blocking)
- Pattern: `register()` in one cell, `sso_get_token()` in next cell after clicking link
- PKCE was active (code_challenge in auth URL)

## What's Broken Now (Jan 2026)

- pygraphistry **0.50.6** (also tested 0.50.5, 0.44.1, 0.45.9)
- Server: `graphistry-pilot.atlas-lion.altana.ai` and `graphistry-dev.grph.xyz`
- Okta: `integrator-*****.okta.com` (via `sso.*****.gov.uk`)
- Both site-wide and org-level SSO fail
- Default `sso_timeout=50` (blocking) in some cases
- "Code verifier required" on the server-side token exchange

## Okta App Configuration

The SSO Admin Guide and Nexus source code confirm:

- **App type must be SPA** (not Web App)
- Okta API: `application_type: "browser"`, `token_endpoint_auth_method: "none"`
- No client secret — PKCE handles auth
- Grant types: `authorization_code` only

We created a corrected Okta app creation script: `okta/okta_create_graphistry_spa.sh`
(old Web App script moved to `okta/old_scripts/`).

However: the current Okta app appears to already be accepting PKCE authorize requests
(the auth URL works, user can authenticate). The failure is on the **server callback**,
not the Okta config.

## Open Questions for Client

1. Export and send the **complete current Databricks notebook** (`.ipynb` or `.dbc`)
2. Which server are you currently using — `graphistry-pilot.atlas-lion.altana.ai` or `graphistry-dev.grph.xyz`?
3. After clicking the SSO link: do you see Okta login, and after authenticating, do you get "login successful" or "Code verifier required"?
4. Does the error happen on first login after fresh cluster start, or only on re-runs?
5. Current `%pip show graphistry` output?

## Open Questions for Engineering (Internal)

1. What is the Django `CACHES` backend on `graphistry-pilot.atlas-lion.altana.ai`? (Must be Redis/Memcached, not LocMemCache)
2. How many Daphne/gunicorn workers are running? (LocMemCache is per-process)
3. Was the server recently restarted or upgraded around Jan 27?
4. Check Okta System Log for errors around Jan 27-30

## Immediate Workaround for Client

Non-blocking SSO pattern (worked with 0.33.8, avoids timeout race):

```python
# Cell 1
%pip install graphistry
dbutils.library.restartPython()

# Cell 2
import graphistry
graphistry.register(
    api=3, protocol="https",
    server="graphistry-pilot.atlas-lion.altana.ai",
    org_name='gsci-pilot',
    is_sso_login=True,
    sso_timeout=None  # non-blocking
)
# Click the SSO link, complete login in browser

# Cell 3 (run after login completes)
graphistry.sso_get_token()
print(f"Token: {str(graphistry.api_token())[:12]}...")

# Cell 4
import pandas as pd
df = pd.read_csv('https://raw.githubusercontent.com/graphistry/pygraphistry/master/demos/data/honeypot.csv')
g = graphistry.edges(df, 'attackerIP', 'victimIP')
g.plot()
```

Note: This workaround only addresses the timing/polling issue. The "Code verifier
required" error is a server-side problem that requires fixing the Django cache backend.

## Resolution (Feb 2, 2026)

### P0 Fix: Redis cache for PKCE code verifier

**File:** `graphistry/apps/core/nexus/config/settings/base.py:900`

Changed Django `CACHES['default']` from `LocMemCache` to `django_redis.cache.RedisCache`.
Redis was already configured as a secondary named cache alias — the fix promotes it to
the default backend so all Gunicorn workers share the `sso_cv_{state}` key.

### Validation

Built Graphistry v2.45.11 from source with the fix, deployed to `obsidian-tc.grph.xyz`,
configured Okta SSO, and ran end-to-end tests:

| Test | Server | Result |
|------|--------|--------|
| `diagnose_sso.py` (9 checks) | `graphistry-dev.grph.xyz` | 9/9 PASS |
| `diagnose_sso.py` (9 checks) | `obsidian-tc.grph.xyz` | 9/9 PASS |
| Error 2 reproduction (polling race) | `obsidian-tc.grph.xyz` | REPRODUCED — "State is invalid" after 15s timeout |
| Error 3 reproduction (login TypeError) | local | REPRODUCED — TypeError as expected |
| Fixed flow (non-blocking SSO) | `obsidian-tc.grph.xyz` | PASSED — token acquired, login succeeded |

### Answers to Open Questions

1. **Django CACHES backend:** Was `LocMemCache` (default). Fixed to `django_redis.cache.RedisCache`.
2. **Multiple workers:** Yes, Gunicorn runs multiple workers. LocMemCache is per-process, causing the verifier loss.
3. **Non-blocking pattern:** `sso_timeout=None` with `sso_get_token()` in a separate cell works correctly.

### Remaining Work

- Apply the Redis cache fix to the client's production server (`graphistry-pilot.atlas-lion.altana.ai`)
- Send client the updated non-blocking notebook pattern
- Verify fix on client's server with `diagnose_sso.py`

## Files in This Repo

```
databricks-sso/
  CLAUDE.md                          # Context for Claude Code sessions
  FINDINGS-databricks-sso-jan30-2026.md  # This file
  databricks_graphistry_sso_test.py  # Simple SSO test script
  from_client/
    error_logging_in_graphistry_gmail_thread_Jan30.pdf
    screenshots/
      databricks_screenshot.png      # Notebook with code + Graphistry login page
      databricks_screenshot2.png     # Same, zoomed view
      databricks_sso_graphistry_successful_login_screenshot.png  # Successful browser login
  from_graphistry/
    test-html-login-link-pygraphistry-0.33.8__May08_2024/
      test-html-login-link-pygraphistry-0.33.8.py    # Working example we sent (May 2024)
      test-html-login-link-pygraphistry-0.33.8.ipynb  # Same, notebook format
      test-html-login-link-pygraphistry-0.33.8.dbc   # Same, Databricks archive
  notebooks/
    diagnose_sso.py                  # SSO diagnostic (9 checks, CLI + API)
    reproduce_sso_errors.py          # Client error reproduction script
    databricks_sso_runbook.ipynb     # Interactive SSO login/validation notebook
    reproduce_sso_errors.ipynb       # Error reproduction notebook for Databricks
    sso-register-example-databricks-tcook-jan30-2026.ipynb  # Our Jan 30 test notebook
  graphistry/                        # Shallow clone of graphistry/graphistry.git (with fix)
  okta/
    README.md
    okta_create_graphistry_spa.sh    # Correct SPA script (PKCE)
    old_scripts/
      okta_create_graphistry_app.sh  # Deprecated Web App script
  graphistry-nexus-copy/             # Nexus server source (for reference)
  pygraphistry/                      # pygraphistry client source (cloned)
  venv-graphistry-0.50.6/            # Local venv with 0.50.6
```
