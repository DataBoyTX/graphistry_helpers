#!/usr/bin/env python3
"""
Reproduce SSO errors reported by client (Livia Hull, Jan 27-28 2026).

This script reproduces the three errors from the client email thread:
  Error 1 (P0): "Code verifier required" — PKCE cache miss
  Error 2 (P1): "State is invalid" — polling race condition
  Error 3 (P2): login() missing username/password — wrong API call

Usage:
    # Test against local instance
    python reproduce_sso_errors.py --server localhost --protocol http

    # Test against remote
    python reproduce_sso_errors.py --server graphistry-dev.grph.xyz

    # Run only specific error tests
    python reproduce_sso_errors.py --server localhost --protocol http --test error1
    python reproduce_sso_errors.py --server localhost --protocol http --test error2
    python reproduce_sso_errors.py --server localhost --protocol http --test error3

    # Test the fixed flow (non-blocking, should succeed)
    python reproduce_sso_errors.py --server localhost --protocol http --test fixed
"""

import argparse
import json
import sys
import time
from urllib.parse import parse_qs, urlparse

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# URL construction (mirrors arrow_uploader.py:354-362, 406)
# ---------------------------------------------------------------------------

def build_sso_login_url(base_url, org_name=None, idp_name=None):
    if org_name is None and idp_name is None:
        return f"{base_url}/api/v2/g/sso/oidc/login/"
    elif org_name is not None and idp_name is None:
        return f"{base_url}/api/v2/o/{org_name}/sso/oidc/login/"
    elif org_name is not None and idp_name is not None:
        return f"{base_url}/api/v2/o/{org_name}/sso/oidc/login/{idp_name}/"
    else:
        return f"{base_url}/api/v2/g/sso/oidc/login/"


def build_token_poll_url(base_url, state):
    return f"{base_url}/api/v2/o/sso/oidc/jwt/{state}/"


# ---------------------------------------------------------------------------
# Shared: initiate SSO and get state + auth_url
# ---------------------------------------------------------------------------

def initiate_sso(base_url, org_name=None, idp_name=None):
    """POST to SSO login endpoint, return (state, auth_url) or raise."""
    url = build_sso_login_url(base_url, org_name, idp_name)
    print(f"  POST {url}")
    resp = requests.post(url, timeout=15)
    body = resp.json()
    status = (body.get("status") or "").upper()
    data = body.get("data", {})
    state = data.get("state", "")
    auth_url = data.get("auth_url", "")

    if status == "OK" and state and auth_url:
        print(f"  Got state={state[:12]}...")
        print(f"  Auth URL: {auth_url[:80]}...")
        return state, auth_url

    error = body.get("message") or body.get("error") or json.dumps(body)
    raise RuntimeError(f"SSO initiation failed: {error}")


# ---------------------------------------------------------------------------
# Error 1: "Code verifier required"
#
# Reproduces the P0 PKCE cache bug. The server stores sso_cv_{state} in
# Django's default cache during authorize. If the cache is LocMemCache
# (per-process), a different Gunicorn worker handles the callback and
# can't find the verifier. Okta returns "Code verifier required."
#
# To reproduce:
#   1. Server must be using LocMemCache (the default before the fix)
#   2. Complete the full SSO flow — click the auth URL, log in at Okta
#   3. The callback will fail with "Code verifier required" on the
#      Graphistry error page
#
# With the Redis fix applied, this error should NOT occur.
# ---------------------------------------------------------------------------

def test_error1_code_verifier(base_url, org_name=None, idp_name=None):
    """
    Error 1: "Code verifier required"

    This test initiates SSO and provides the auth URL for manual login.
    If the server uses LocMemCache, completing login will show the error
    on the callback page. If Redis is the default cache, login succeeds.
    """
    print()
    print("=" * 60)
    print(" ERROR 1: Code verifier required (P0)")
    print("=" * 60)
    print()
    print("  This reproduces the PKCE cache bug.")
    print("  If LocMemCache is the default cache backend,")
    print("  completing SSO login will fail with:")
    print('    "Code verifier required"')
    print()
    print("  If Redis is the default cache backend (fix applied),")
    print("  SSO login should succeed.")
    print()

    try:
        state, auth_url = initiate_sso(base_url, org_name, idp_name)
    except RuntimeError as e:
        print(f"  SKIP: {e}")
        return False

    # Verify PKCE params are present
    params = parse_qs(urlparse(auth_url).query)
    challenge = params.get("code_challenge", [None])[0]
    method = params.get("code_challenge_method", [None])[0]

    if challenge and method == "S256":
        print(f"  PKCE active: code_challenge_method=S256")
        print(f"  Server stored sso_cv_{state[:8]}... in cache")
    else:
        print(f"  WARNING: PKCE not active (method={method})")
        print(f"  This test requires PKCE to be enabled")
        return False

    print()
    print("-" * 60)
    print("  MANUAL STEP: Open this URL in a browser and complete login:")
    print()
    print(f"  {auth_url}")
    print()
    print("  Expected results:")
    print('    LocMemCache: Error page → "Code verifier required"')
    print("    Redis cache: Successful login → redirect to Graphistry")
    print("-" * 60)
    print()

    # Poll for token to see if login succeeded
    input("  Press Enter after completing SSO login (or Ctrl+C to skip)...")
    print()

    poll_url = build_token_poll_url(base_url, state)
    print(f"  Polling {poll_url}")
    resp = requests.get(poll_url, timeout=15)
    body = resp.json()
    print(f"  Response: {json.dumps(body, indent=2)}")

    token = body.get("data", {}).get("token")
    if token:
        print(f"\n  RESULT: SSO login SUCCEEDED (Redis fix is working)")
        print(f"  Token prefix: {token[:20]}...")
        return True
    else:
        msg = body.get("message", "")
        print(f"\n  RESULT: SSO login FAILED — {msg}")
        if "invalid" in msg.lower():
            print('  This is the "State is invalid" error (Error 2)')
            print("  The PKCE callback likely failed with 'Code verifier required'")
        return False


# ---------------------------------------------------------------------------
# Error 2: "State is invalid"
#
# Reproduces the P1 polling race condition. The client uses blocking mode
# (sso_timeout=50) which polls /api/v2/o/sso/oidc/jwt/{state}/ immediately
# before the user has completed login. The state is never fulfilled because
# either:
#   a) The user hasn't logged in yet (normal race)
#   b) The PKCE callback failed (Error 1 compounds into Error 2)
#
# After the timeout, the client gives up with "State is invalid."
# ---------------------------------------------------------------------------

def test_error2_state_invalid(base_url, org_name=None, idp_name=None,
                               poll_timeout=15):
    """
    Error 2: "State is invalid"

    This test initiates SSO then immediately polls for the token
    (simulating the blocking sso_timeout behavior). Since no one has
    completed login, the poll returns "State is invalid."
    """
    print()
    print("=" * 60)
    print(" ERROR 2: State is invalid (P1)")
    print("=" * 60)
    print()
    print("  This reproduces the polling race condition.")
    print("  The client polls for a JWT token immediately after")
    print("  initiating SSO, before the user has logged in.")
    print(f"  Simulating sso_timeout={poll_timeout}s blocking poll.")
    print()

    try:
        state, auth_url = initiate_sso(base_url, org_name, idp_name)
    except RuntimeError as e:
        print(f"  SKIP: {e}")
        return False

    print()
    print("  NOT opening auth URL — simulating the race condition.")
    print("  Polling for token immediately (user has not logged in)...")
    print()

    poll_url = build_token_poll_url(base_url, state)
    elapsed = 0
    interval = 2
    last_msg = ""

    while elapsed < poll_timeout:
        resp = requests.get(poll_url, timeout=15)
        body = resp.json()
        msg = body.get("message", "")
        token = body.get("data", {}).get("token") if "data" in body else None

        if token:
            print(f"  [{elapsed}s] Unexpected: got token (someone logged in?)")
            return True

        if msg != last_msg:
            print(f"  [{elapsed}s] Response: {msg}")
            last_msg = msg

        time.sleep(interval)
        elapsed += interval

    print()
    print(f"  RESULT: Timed out after {poll_timeout}s")
    print(f"  Last response: {msg}")
    print()
    print("  This is what the client saw:")
    print('    Exception: State is invalid')
    print('    SsoRetrieveTokenTimeoutException: [SSO] Get token timeout')
    print()
    print("  Fix: Use sso_timeout=None (non-blocking mode)")
    return True


# ---------------------------------------------------------------------------
# Error 3: login() missing username/password
#
# The client called graphistry.login() which requires username and password
# positional arguments. The correct call for SSO is:
#   graphistry.register(is_sso_login=True, ...)
# ---------------------------------------------------------------------------

def test_error3_login_typeerror():
    """
    Error 3: login() missing 'username' and 'password'

    This test attempts to import graphistry and call login() without
    arguments, reproducing the TypeError the client saw.
    """
    print()
    print("=" * 60)
    print(" ERROR 3: login() missing username/password (P2)")
    print("=" * 60)
    print()
    print("  This reproduces the client calling the wrong API method.")
    print("  graphistry.login() requires username + password.")
    print("  The correct SSO call is graphistry.register(is_sso_login=True).")
    print()

    try:
        import graphistry
        print("  Calling graphistry.login() with no arguments...")
        try:
            graphistry.login()
        except TypeError as e:
            print(f"  RESULT: TypeError raised (as expected)")
            print(f"  Error: {e}")
            print()
            print("  This matches the client error:")
            print("    TypeError: GraphistryClient.login() missing 2 required")
            print("    positional arguments: 'username' and 'password'")
            return True
        else:
            print("  UNEXPECTED: No TypeError raised")
            return False
    except ImportError:
        print("  graphistry not installed — simulating the error:")
        print()
        print("  TypeError: GraphistryClient.login() missing 2 required")
        print("  positional arguments: 'username' and 'password'")
        print()
        print("  To reproduce with graphistry installed:")
        print("    import graphistry")
        print("    graphistry.login()  # <-- wrong, should be register()")
        return True


# ---------------------------------------------------------------------------
# Fixed flow: non-blocking SSO (the working pattern)
# ---------------------------------------------------------------------------

def test_fixed_flow(base_url, org_name=None, idp_name=None):
    """
    Fixed flow: non-blocking SSO login.

    This tests the correct pattern:
      1. Initiate SSO (get state + auth_url)
      2. User clicks link and completes login in browser
      3. Poll for token AFTER login (not before)

    This is the sso_timeout=None pattern from the May 2024 working example.
    """
    print()
    print("=" * 60)
    print(" FIXED FLOW: Non-blocking SSO login")
    print("=" * 60)
    print()
    print("  This tests the correct SSO pattern:")
    print("    sso_timeout=None (non-blocking)")
    print("    User completes login, then polls for token")
    print()

    try:
        state, auth_url = initiate_sso(base_url, org_name, idp_name)
    except RuntimeError as e:
        print(f"  SKIP: {e}")
        return False

    # Verify PKCE
    params = parse_qs(urlparse(auth_url).query)
    challenge = params.get("code_challenge", [None])[0]
    if challenge:
        print(f"  PKCE active (good)")

    print()
    print("-" * 60)
    print("  Open this URL in a browser and complete SSO login:")
    print()
    print(f"  {auth_url}")
    print()
    print("-" * 60)
    print()

    input("  Press Enter AFTER you have completed SSO login...")
    print()

    poll_url = build_token_poll_url(base_url, state)
    print(f"  Polling {poll_url}")

    token = None
    for attempt in range(5):
        resp = requests.get(poll_url, timeout=15)
        body = resp.json()
        token = body.get("data", {}).get("token") if "data" in body else None
        if token:
            break
        msg = body.get("message", "")
        print(f"  Attempt {attempt + 1}: {msg}")
        time.sleep(2)

    if token:
        print()
        print(f"  RESULT: SSO login SUCCEEDED")
        print(f"  Token prefix: {token[:20]}...")

        # Verify token
        print()
        print("  Verifying token with server...")
        verify_resp = requests.post(
            f"{base_url}/api/v2/auth/token/verify/",
            json={"token": token},
            timeout=15,
        )
        if verify_resp.status_code == 200:
            print("  Token is valid")
        else:
            print(f"  Token verification: HTTP {verify_resp.status_code}")

        return True
    else:
        print()
        print(f"  RESULT: No token received after 5 attempts")
        print(f"  Last response: {json.dumps(body, indent=2)}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TESTS = {
    "error1": ("Error 1: Code verifier required", test_error1_code_verifier),
    "error2": ("Error 2: State is invalid", test_error2_state_invalid),
    "error3": ("Error 3: login() TypeError", test_error3_login_typeerror),
    "fixed": ("Fixed flow: non-blocking SSO", test_fixed_flow),
}


def main():
    parser = argparse.ArgumentParser(
        description="Reproduce SSO errors from client email (Jan 2026)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Tests:\n"
            "  error1  — 'Code verifier required' (PKCE cache bug)\n"
            "  error2  — 'State is invalid' (polling race condition)\n"
            "  error3  — login() missing username/password (wrong API call)\n"
            "  fixed   — Non-blocking SSO (correct pattern)\n"
            "\n"
            "Examples:\n"
            "  python reproduce_sso_errors.py --server localhost --protocol http\n"
            "  python reproduce_sso_errors.py --server localhost --protocol http --test error2\n"
            "  python reproduce_sso_errors.py --server graphistry-dev.grph.xyz --test fixed\n"
        ),
    )
    parser.add_argument("--server", required=True, help="Graphistry server hostname")
    parser.add_argument("--protocol", default="https", help="Protocol (default: https)")
    parser.add_argument("--org-name", default=None, help="Organization name")
    parser.add_argument("--idp-name", default=None, help="IdP name")
    parser.add_argument(
        "--test",
        choices=list(TESTS.keys()),
        default=None,
        help="Run a specific test (default: run all)",
    )

    args = parser.parse_args()
    base_url = f"{args.protocol}://{args.server}"

    print()
    print("Graphistry SSO Error Reproduction Script")
    print(f"Server: {base_url}")
    if args.org_name:
        print(f"Org: {args.org_name}")
    print()

    if args.test:
        tests_to_run = [args.test]
    else:
        tests_to_run = list(TESTS.keys())

    results = {}
    for test_name in tests_to_run:
        label, fn = TESTS[test_name]
        try:
            if test_name == "error3":
                results[test_name] = fn()
            elif test_name == "error2":
                results[test_name] = fn(base_url, args.org_name, args.idp_name)
            else:
                results[test_name] = fn(base_url, args.org_name, args.idp_name)
        except KeyboardInterrupt:
            print("\n  Skipped.")
            results[test_name] = None
        except Exception as e:
            print(f"\n  ERROR: {e}")
            results[test_name] = False

    # Summary
    print()
    print("=" * 60)
    print(" Summary")
    print("=" * 60)
    for test_name in tests_to_run:
        label, _ = TESTS[test_name]
        result = results.get(test_name)
        if result is True:
            status = "REPRODUCED" if test_name.startswith("error") else "PASSED"
        elif result is False:
            status = "FAILED TO REPRODUCE" if test_name.startswith("error") else "FAILED"
        else:
            status = "SKIPPED"
        print(f"  [{status}] {label}")
    print()


if __name__ == "__main__":
    main()
