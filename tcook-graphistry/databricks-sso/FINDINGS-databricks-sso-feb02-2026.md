# Databricks SSO Iframe Regression — Findings

## Problem Statement

After upgrading the Graphistry server, `g.plot()` in Databricks notebooks shows a
Graphistry login page in the iframe instead of the visualization. SSO login succeeds,
data uploads succeed, but the iframe cannot authenticate to display the visualization.

**Client report (Livia Hull, DBT, Jan 30 2026):**
> "When I log in first time in Graphistry I can see: Welcome to Graphistry Enterprise.
> And it's only when I try to visualise the plot in Graphistry it's asking me to log in
> again. This is something that didn't happen before the upgrade."

**David Hutchinson (DBT):**
> "We have tested against the latest version of the library (0.50.5), and that doesn't
> work. The latest version that works is 0.45.9."

Workaround: `pip install graphistry==0.44.1`

## Root Cause: Cross-Origin Cookie Blocking (SameSite=Lax)

### The actual mechanism

Databricks live test confirms: **both 0.45.9 and 0.45.10 SSO + plot upload succeed,
but BOTH show a login page in the iframe.** Adding `graphistry.privacy(mode='public')`
makes the viz appear. This proves the issue is NOT a pygraphistry version change.

The iframe flow:
1. Databricks notebook (on `dbc-xxx.cloud.databricks.com`) renders an iframe
2. iframe `src` points to `https://graphistry-server/graph/graph.html?dataset=xxx`
3. `graph.html` JavaScript makes API calls: `GET /api/v2/datasets/xxx/`
4. **Browser blocks session cookies** on these cross-origin requests (`SameSite=Lax`)
5. Graphistry API returns 401 → JavaScript shows login page instead of viz
6. `privacy(mode='public')` bypasses auth → API returns data without cookies → works

### Why it broke during the upgrade

The Graphistry server cookie configuration (`config/settings/base.py:873-879`):
```python
# Allow cross-origin embedded logins when COOKIE_SECURE=True and COOKIE_SAMESITE='None'
SESSION_COOKIE_SAMESITE = 'None' if COOKIE_SECURE else 'Lax'
CSRF_COOKIE_SAMESITE = 'None' if COOKIE_SECURE else 'Lax'
```

Default: `COOKIE_SECURE=False` → `SameSite=Lax` → cross-origin iframes blocked.

The **previous server installation** likely had `COOKIE_SECURE=True` (or browsers
were more lenient with `SameSite` before). The upgrade reset this to the default `False`.

### The fix

**Set `COOKIE_SECURE=True` in the Graphistry server environment.** This:
- Sets `SameSite=None` on all cookies (session, CSRF, JWT)
- Allows cross-origin iframes (Databricks → Graphistry) to send cookies
- Requires HTTPS (which the server already uses)

The server already has this built in — it just needs the env var:
```bash
COOKIE_SECURE=True
```

Relevant server code:
- `config/settings/base.py:874`: `SESSION_COOKIE_SECURE = env.bool('COOKIE_SECURE', False)`
- `config/settings/base.py:878`: `SESSION_COOKIE_SAMESITE = 'None' if COOKIE_SECURE else 'Lax'`
- `config/settings/base.py:188-191`: JWT cookie SameSite follows same logic
- `graphistry/views.py:30`: `@xframe_options_exempt` on DashboardView (iframes allowed)

### Caddy reverse proxy: X-Frame-Options blocks iframe (second layer)

The Caddyfile (`data/config/Caddyfile:31`) adds `X-Frame-Options: SAMEORIGIN` on
ALL responses, overriding Django's `@xframe_options_exempt` on the graph view.

Verified via response headers:
```
obsidian-tc.grph.xyz  → X-Frame-Options: SAMEORIGIN  (iframe BLOCKED from Databricks)
graphistry-dev.grph.xyz → X-Frame-Options: ALLOWALL   (iframe allowed)
```

Both servers have `SameSite=Lax` on cookies (cross-origin cookie sending blocked).

### Both fixes are required

| Fix | What | Where | Effect |
|-----|------|-------|--------|
| **Caddyfile** | `X-Frame-Options ALLOWALL` | `data/config/Caddyfile:31` | Browser renders iframe |
| **Django env** | `COOKIE_SECURE=True` | Server environment | Cookies sent cross-origin |

Without the Caddy fix: browser refuses to render the iframe entirely.
Without the cookie fix: iframe renders but API calls lack auth → login page.

### Server settings that matter

| Setting | Default | Required for iframes |
|---------|---------|---------------------|
| Caddy `X-Frame-Options` | `SAMEORIGIN` | `ALLOWALL` (or remove) |
| `COOKIE_SECURE` | `False` | `True` |
| `SESSION_COOKIE_SAMESITE` | `Lax` | `None` (auto when COOKIE_SECURE=True) |
| `CSRF_COOKIE_SAMESITE` | `Lax` | `None` (auto) |
| `JWT_AUTH_COOKIE_SAMESITE` | `Lax` | `None` (auto) |
| `X_FRAME_OPTIONS` (Django) | `DENY` | Already exempt for graph views |

## Ruled-Out Hypotheses

### Privacy defaults: RULED OUT

Local venv comparison across 0.44.1, 0.45.9, and 0.50.6 shows identical privacy code:
- `PlotterBase._privacy = None` in all versions
- `cascade_privacy_settings()` defaults to `mode='private'` in all versions
- `maybe_post_share_link()` guard identical (only fires if `.privacy()` explicitly called)

### pygraphistry version regression: RULED OUT

Databricks live test: both 0.45.9 and 0.45.10 show the same behavior (SSO OK, plot OK,
iframe shows login page). The issue is server-side, not client-side.

The `active_organization` and `_switch_org()` changes in 0.45.10+ are real breaking
changes but are **not the cause of this specific issue.** They may cause SSO failures
on servers that don't return `active_organization` in the JWT response, but that's a
separate problem from the iframe auth issue.

### viztoken: NOT AN AUTH MECHANISM

The `viztoken` in plot URLs (`?viztoken=uuid`) is a client-generated `uuid.uuid4()` at
`PlotterBase.py:2191`. It has no server-side counterpart and provides no authentication.
The Graphistry `graph.html` frontend relies on session cookies for API auth.

## Version Bisect (Static Analysis)

While not the cause of the iframe issue, these are real API breaking changes:

| Version | `active_org` required | `_switch_org` | ApiVersion | Status |
|---------|----------------------|---------------|------------|--------|
| 0.44.1 | No (optional) | No | Literal[1,3] | OK |
| 0.45.9 | No (optional) | No | Literal[1,3] | OK |
| **0.45.10** | **YES (raises)** | **YES** | Literal[1,3] | SSO may crash |
| 0.47.0+ | YES | YES | **Literal[3]** | SSO may crash + API v3 only |

## Client Error Timeline (Jan 27-30 2026)

1. **Jan 27, Livia:** `graphistry.login()` TypeError — called without args
2. **Jan 27, David:** "State is invalid" with 0.50.5 — SSO polling race
3. **Jan 28, Livia:** "Code verifier required" — PKCE LocMemCache issue (fixed: Redis)
4. **Jan 30, Livia:** Login works, iframe shows login — **cross-origin cookie issue**

## Fix Applied and Verified (obsidian-tc.grph.xyz, Feb 2 2026)

### Changes applied

**1. Caddyfile** (`graphistry_v2.45.3-12.8--TEST_BUILD_SSO/data/config/Caddyfile:31`):
```diff
-        header_down X-Frame-Options SAMEORIGIN
+        header_down X-Frame-Options ALLOWALL
```

**2. custom.env** (`graphistry_v2.45.3-12.8--TEST_BUILD_SSO/data/config/custom.env`):
```
COOKIE_SECURE=True
```

**3. Restart:** `docker compose stop && docker compose up -d`

### Verification (curl response headers)

Before fix:
```
x-frame-options: SAMEORIGIN
set-cookie: csrftoken=...; SameSite=Lax
```

After fix:
```
x-frame-options: ALLOWALL
set-cookie: csrftoken=...; SameSite=None; Secure
```

Both headers confirmed changed on `obsidian-tc.grph.xyz` immediately after restart.

### Databricks test notebook

Pushed `test_iframe_fix_obsidian_tc` to Databricks for end-to-end verification:
- Path: `/Workspace/Users/tcook@graphistry.com/SSO-register/DBT/claude/test_iframe_fix_obsidian_tc`
- Server: `obsidian-tc.grph.xyz`
- Tests: 3 iframes rendered side-by-side (no privacy, public, private)
- Expected: all 3 show visualization (no login page) now that cookies are sent cross-origin

### Databricks Test Results (Feb 3 2026)

#### Test 1: `graphistry-dev.grph.xyz` (baseline - has `X-Frame-Options: ALLOWALL` but `SameSite=Lax`)

| Test | Privacy | Result | Explanation |
|------|---------|--------|-------------|
| A | none (default) | **FAIL** (login page) | Unauthenticated request, private default |
| B | `mode='public'` | **PASS** (viz renders) | No auth needed for public datasets |
| C | `mode='private'` | **FAIL** (login page) | Unauthenticated request can't access private |

This confirms that with `SameSite=Lax`, cross-origin iframes cannot send cookies,
so private datasets require re-login in the iframe.

#### Test 2: `obsidian-tc.grph.xyz` (has both fixes applied)

**Headers verified correct:**
```
x-frame-options: ALLOWALL
set-cookie: csrftoken=...; SameSite=None; Secure
```

**BUT SSO/org authorization blocks dataset creation:**
```
ERROR: HTTP 403 - Dataset creation encountered an authorization error
Server logs: "Organization with slug None not found"
```

The SSO user authenticates successfully but has no org context in the JWT.
This is a **separate server configuration issue** unrelated to the iframe fix.

### FIX VERIFIED — All three iframes render visualization (Feb 3 2026)

**Final test on `obsidian-tc.grph.xyz` with all fixes applied:**

| Test | Privacy | `requests.get()` | Actual Iframe |
|------|---------|------------------|---------------|
| A | none (default) | FAIL (no cookies) | **PASS** ✓ |
| B | `mode='public'` | PASS | **PASS** ✓ |
| C | `mode='private'` | FAIL (no cookies) | **PASS** ✓ |

The `requests.get()` check shows FAIL for A and C because it doesn't send cookies.
The **actual Databricks iframes** render all three visualizations correctly because
browsers send `SameSite=None; Secure` cookies on cross-origin iframe requests.

### Three issues identified and fixed

| Issue | Layer | Status | Fix |
|-------|-------|--------|-----|
| 1. X-Frame-Options blocking | Caddy proxy | **FIXED** ✓ | `header_down X-Frame-Options ALLOWALL` |
| 2. SameSite=Lax blocking cookies | Django env | **FIXED** ✓ | `COOKIE_SECURE=True` → `SameSite=None` |
| 3. SSO org context missing | User config | **FIXED** ✓ | Set user's `default_organization` to personal org (not SITE) |

All three fixes are required for Databricks iframe visualization to work with private datasets.

## Recommended Fixes

### P0: Server-side fix (resolves iframe issue) — THREE CHANGES

**1. Caddyfile: Allow cross-origin iframes**
```
# In data/config/Caddyfile, change:
header_down X-Frame-Options SAMEORIGIN
# To:
header_down X-Frame-Options ALLOWALL
```
Then restart Caddy: `docker compose stop caddy && docker compose up -d`

**2. Django environment: Enable cross-origin cookies**
Add to `data/config/custom.env`:
```bash
COOKIE_SECURE=True
```
This enables `SameSite=None` for all cookies, allowing Databricks iframes to
authenticate. Requires HTTPS (already in use).

Then restart all services: `docker compose stop && docker compose up -d`

**3. User organization config: Set default_organization to non-SITE org**
For users authenticating via site-wide SSO, their `default_organization` must NOT
be the SITE org (site-wide org cannot be used as active org for dataset creation).

Fix via Django admin or shell:
```python
user.default_organization = user.organization  # personal org
user.save()
```

Or ensure new SSO users are automatically assigned to a non-SITE default org.

### P1: Client-side privacy workaround (temporary)
If server fix cannot be deployed immediately:
```python
g.privacy(mode='public').plot()
```
Datasets will be publicly accessible (may not be acceptable for sensitive data).

### P2: Consider `organization` privacy mode
```python
g.privacy(mode='organization').plot()
```
This still requires auth (won't work without the server fix), but is more restrictive
than `public`. Only useful after `COOKIE_SECURE=True` is set.

### P3: pygraphistry active_organization regression
For servers that don't return `active_organization` in SSO response, 0.45.10+ will
crash. Options:
- Pin to 0.45.9
- Fix server to return `active_organization` in JWT response
- Fix pygraphistry to make `active_organization` optional again

## Test Artifacts

| File | Purpose |
|------|---------|
| `scripts/compare_privacy_defaults.py` | Run in each venv to compare privacy defaults |
| `scripts/automated_version_bisect.py` | Automated version bisect (SSO once, test all) |
| `scripts/push_notebook.py` | Upload notebooks to Databricks workspace |
| `notebooks/test_privacy_iframe.ipynb` | Privacy + iframe test matrix (Databricks) |
| `notebooks/test_iframe_fix_obsidian_tc.ipynb` | Fix verification against obsidian-tc (Databricks) |
| `notebooks/test_version_bisect.ipynb` | Version bisect with live SSO (Databricks) |
| `FINDINGS-databricks-sso-feb02-2026.md` | This file |
| `venv-0.44.1/`, `venv-0.45.9/`, `venv-0.50.6/` | Version comparison environments |

## Key Server Code References

- `data/config/Caddyfile:31` — X-Frame-Options (SAMEORIGIN blocks Databricks iframe)
- `config/settings/base.py:873-879` — Cookie SameSite configuration
- `config/settings/base.py:188-191` — JWT cookie SameSite
- `config/settings/production.py:108` — X_FRAME_OPTIONS = 'DENY'
- `graphistry/views.py:30` — `@xframe_options_exempt` on graph views
- `viz/models.py:78-95` — Default share link privacy (PRIVATE for personal orgs)
- `permissions/consts.py:7-11` — Privacy mode constants (PUBLIC, PRIVATE, ORGANIZATION)
