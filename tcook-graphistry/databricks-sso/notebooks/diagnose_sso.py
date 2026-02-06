#!/usr/bin/env python3
"""
Graphistry SSO Diagnostic Script

Standalone diagnostic tool for troubleshooting Graphistry SSO configuration.
Only dependency: requests. No graphistry import needed.

Environment variables:
    GRAPHISTRY_SERVER   — Server hostname (default: obsidian-tc.grph.xyz)
    GRAPHISTRY_PROTOCOL — Protocol (default: https)

CLI usage:
    python diagnose_sso.py
    python diagnose_sso.py --server graphistry-dev.grph.xyz
    python diagnose_sso.py --server localhost --protocol http --json

Importable API:
    from diagnose_sso import run_diagnostic
    report = run_diagnostic(server="obsidian-tc.grph.xyz")
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

DEFAULT_SERVER = os.environ.get("GRAPHISTRY_SERVER", "obsidian-tc.grph.xyz")
DEFAULT_PROTOCOL = os.environ.get("GRAPHISTRY_PROTOCOL", "https")

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package is required. Install with: pip install requests")
    sys.exit(1)

DIAGNOSE_SSO_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Known issues — data-driven hint generation
# ---------------------------------------------------------------------------

KNOWN_ISSUES: Dict[str, Dict[str, str]] = {
    "code_verifier_required": {
        "symptom": "After clicking SSO link: 'Code verifier required'",
        "cause": (
            "Django CACHES backend is LocMemCache (per-process). "
            "Worker A stores sso_cv_{state} during authorize, but Worker B "
            "handles the callback and cannot find it."
        ),
        "fix": "Set Django CACHES default backend to Redis or Memcached on the Graphistry server.",
    },
    "state_invalid_immediately": {
        "symptom": "Token poll returns 'State is invalid' right away",
        "cause": "State was not persisted server-side, or cache/worker mismatch lost it.",
        "fix": "Ensure shared cache backend (Redis/Memcached) and consistent routing.",
    },
    "sso_timeout_race": {
        "symptom": "Blocking sso_timeout polls before user finishes login, then times out",
        "cause": "Default sso_timeout=50 starts polling immediately.",
        "fix": "Use sso_timeout=None (non-blocking) and call graphistry.sso_get_token() after login.",
    },
}


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

class CheckResult:
    """Result of a single diagnostic check."""

    def __init__(
        self,
        name: str,
        passed: bool,
        detail: str = "",
        duration_ms: Optional[float] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.passed = passed
        self.detail = detail
        self.duration_ms = duration_ms
        self.data = data or {}

    @property
    def status_label(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
        }
        if self.duration_ms is not None:
            d["duration_ms"] = round(self.duration_ms, 1)
        if self.data:
            d["data"] = self.data
        return d

    def __str__(self) -> str:
        timing = ""
        if self.duration_ms is not None:
            timing = f", {self.duration_ms:.0f}ms"
        detail = f" ({self.detail})" if self.detail else ""
        return f"[{self.status_label}] {self.name}{detail}{timing}"


class Hint:
    """A server-side hint inferred from client observations."""

    def __init__(self, level: str, message: str, issue_key: Optional[str] = None):
        self.level = level  # WARN or INFO
        self.message = message
        self.issue_key = issue_key

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"level": self.level, "message": self.message}
        if self.issue_key and self.issue_key in KNOWN_ISSUES:
            d["known_issue"] = KNOWN_ISSUES[self.issue_key]
        return d

    def __str__(self) -> str:
        extra = ""
        if self.issue_key and self.issue_key in KNOWN_ISSUES:
            ki = KNOWN_ISSUES[self.issue_key]
            extra = f"\n         Cause: {ki['cause']}\n         Fix:   {ki['fix']}"
        return f"[{self.level}] {self.message}{extra}"


# ---------------------------------------------------------------------------
# URL construction — mirrors arrow_uploader.py:354-362
# ---------------------------------------------------------------------------

def build_base_url(server: str, protocol: str = "https") -> str:
    return f"{protocol}://{server}"


def build_sso_login_url(
    base_url: str,
    org_name: Optional[str] = None,
    idp_name: Optional[str] = None,
) -> str:
    """Build the SSO login initiation URL.

    Mirrors pygraphistry arrow_uploader.py:354-362 exactly.
    """
    if org_name is None and idp_name is None:
        return f"{base_url}/api/v2/g/sso/oidc/login/"
    elif org_name is not None and idp_name is None:
        return f"{base_url}/api/v2/o/{org_name}/sso/oidc/login/"
    elif org_name is not None and idp_name is not None:
        return f"{base_url}/api/v2/o/{org_name}/sso/oidc/login/{idp_name}/"
    else:
        # idp_name without org_name — fall back to site-wide
        return f"{base_url}/api/v2/g/sso/oidc/login/"


def build_token_poll_url(base_url: str, state: str) -> str:
    """Build the token polling URL.

    Mirrors arrow_uploader.py:406 exactly.
    """
    return f"{base_url}/api/v2/o/sso/oidc/jwt/{state}/"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_server_reachable(base_url: str) -> CheckResult:
    """Check 1: Server reachable via GET."""
    t0 = time.time()
    try:
        resp = requests.get(base_url, timeout=15, allow_redirects=True)
        ms = (time.time() - t0) * 1000
        if resp.status_code < 400:
            return CheckResult(
                "Server reachable",
                True,
                f"{resp.status_code} OK",
                ms,
            )
        return CheckResult(
            "Server reachable",
            False,
            f"HTTP {resp.status_code}",
            ms,
        )
    except requests.RequestException as e:
        ms = (time.time() - t0) * 1000
        return CheckResult("Server reachable", False, str(e), ms)


def check_sso_login_endpoint(
    base_url: str,
    org_name: Optional[str] = None,
    idp_name: Optional[str] = None,
) -> CheckResult:
    """Check 2: SSO login initiation returns state + auth_url."""
    url = build_sso_login_url(base_url, org_name, idp_name)
    t0 = time.time()
    try:
        resp = requests.post(url, timeout=15)
        ms = (time.time() - t0) * 1000
        try:
            body = resp.json()
        except ValueError:
            return CheckResult(
                "SSO login endpoint",
                False,
                f"Non-JSON response (HTTP {resp.status_code})",
                ms,
            )

        # Successful response has {status: "OK", data: {state, auth_url}}
        status = body.get("status") or body.get("Status", "")
        data = body.get("data", {})
        state = data.get("state", "")
        auth_url = data.get("auth_url", "")

        if status.upper() == "OK" and state and auth_url:
            return CheckResult(
                "SSO login endpoint",
                True,
                f"state={state[:12]}...",
                ms,
                data={"state": state, "auth_url": auth_url, "body": body},
            )

        # Error response
        error_msg = body.get("message") or body.get("error") or json.dumps(body)
        return CheckResult(
            "SSO login endpoint",
            False,
            f"Unexpected response: {error_msg}",
            ms,
            data={"body": body},
        )
    except requests.RequestException as e:
        ms = (time.time() - t0) * 1000
        return CheckResult("SSO login endpoint", False, str(e), ms)


def check_auth_url_pkce(auth_url: str) -> CheckResult:
    """Check 3: Auth URL contains PKCE code_challenge."""
    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)
    challenge = params.get("code_challenge", [None])[0]
    method = params.get("code_challenge_method", [None])[0]

    if challenge and method == "S256":
        return CheckResult(
            "Auth URL has PKCE",
            True,
            f"code_challenge_method=S256, challenge={challenge[:12]}...",
            data={"code_challenge": challenge, "code_challenge_method": method},
        )
    if challenge:
        return CheckResult(
            "Auth URL has PKCE",
            True,
            f"code_challenge_method={method}",
            data={"code_challenge": challenge, "code_challenge_method": method},
        )
    return CheckResult(
        "Auth URL has PKCE",
        False,
        "No code_challenge in auth URL — server not using PKCE",
    )


def check_auth_url_client_id(auth_url: str) -> CheckResult:
    """Check 4: Auth URL contains client_id."""
    params = parse_qs(urlparse(auth_url).query)
    client_id = params.get("client_id", [None])[0]
    if client_id:
        return CheckResult(
            "Auth URL client_id",
            True,
            f"client_id={client_id[:12]}...",
            data={"client_id": client_id},
        )
    return CheckResult("Auth URL client_id", False, "No client_id in auth URL")


def check_auth_url_redirect_uri(auth_url: str, server: str) -> CheckResult:
    """Check 5: Auth URL redirect_uri matches expected pattern."""
    params = parse_qs(urlparse(auth_url).query)
    redirect_uri = params.get("redirect_uri", [None])[0]
    if not redirect_uri:
        return CheckResult(
            "Auth URL redirect_uri", False, "No redirect_uri in auth URL"
        )

    # Expected: https://{server}/.../login/callback/
    parsed_redir = urlparse(redirect_uri)
    hostname_match = server in parsed_redir.netloc
    has_callback = parsed_redir.path.rstrip("/").endswith("/login/callback")

    if hostname_match and has_callback:
        return CheckResult(
            "Auth URL redirect_uri",
            True,
            redirect_uri,
            data={"redirect_uri": redirect_uri},
        )

    issues = []
    if not hostname_match:
        issues.append(f"hostname mismatch: expected '{server}', got '{parsed_redir.netloc}'")
    if not has_callback:
        issues.append(f"path does not end with /login/callback/: {parsed_redir.path}")
    return CheckResult(
        "Auth URL redirect_uri",
        False,
        "; ".join(issues),
        data={"redirect_uri": redirect_uri},
    )


def check_auth_url_scopes(auth_url: str) -> CheckResult:
    """Check 6: Auth URL scope includes openid profile email."""
    params = parse_qs(urlparse(auth_url).query)
    scope_str = params.get("scope", [""])[0]
    scopes = set(scope_str.split())
    required = {"openid", "profile", "email"}
    missing = required - scopes

    if not missing:
        return CheckResult(
            "Auth URL scopes",
            True,
            f"scope={scope_str}",
            data={"scope": scope_str},
        )
    return CheckResult(
        "Auth URL scopes",
        False,
        f"Missing scopes: {', '.join(sorted(missing))} (got: {scope_str})",
        data={"scope": scope_str, "missing": sorted(missing)},
    )


def check_auth_url_response_type(auth_url: str) -> CheckResult:
    """Check 7: Auth URL response_type=code."""
    params = parse_qs(urlparse(auth_url).query)
    rt = params.get("response_type", [None])[0]
    if rt == "code":
        return CheckResult("Auth URL response_type", True, "response_type=code")
    return CheckResult(
        "Auth URL response_type",
        False,
        f"Expected response_type=code, got: {rt}",
    )


def check_idp_reachable(auth_url: str) -> CheckResult:
    """Check 8: IdP domain is reachable."""
    parsed = urlparse(auth_url)
    idp_domain = f"{parsed.scheme}://{parsed.netloc}"
    t0 = time.time()
    try:
        resp = requests.head(idp_domain, timeout=10, allow_redirects=True)
        ms = (time.time() - t0) * 1000
        return CheckResult(
            "IdP domain reachable",
            True,
            f"{parsed.netloc} → HTTP {resp.status_code}",
            ms,
            data={"idp_domain": idp_domain},
        )
    except requests.RequestException as e:
        ms = (time.time() - t0) * 1000
        return CheckResult(
            "IdP domain reachable",
            False,
            f"{parsed.netloc} → {e}",
            ms,
            data={"idp_domain": idp_domain},
        )


def check_token_poll(base_url: str, state: str) -> CheckResult:
    """Check 9: Token poll endpoint responds (expects 'State is invalid' without auth)."""
    url = build_token_poll_url(base_url, state)
    t0 = time.time()
    try:
        resp = requests.get(url, timeout=15)
        ms = (time.time() - t0) * 1000
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text[:500]}

        # We expect a response — the exact error message may vary
        return CheckResult(
            "Token poll endpoint",
            True,
            f"HTTP {resp.status_code} (expected — SSO not completed)",
            ms,
            data={"response": body},
        )
    except requests.RequestException as e:
        ms = (time.time() - t0) * 1000
        return CheckResult("Token poll endpoint", False, str(e), ms)


# ---------------------------------------------------------------------------
# Hint rules pipeline
# ---------------------------------------------------------------------------

HintRuleFn = Callable[[List[CheckResult]], Optional[Hint]]

def hint_pkce_cache_issue(results: List[CheckResult]) -> Optional[Hint]:
    """If PKCE is active, warn about potential LocMemCache issue."""
    for r in results:
        if r.name == "Auth URL has PKCE" and r.passed:
            return Hint(
                "WARN",
                (
                    "PKCE is active. If 'Code verifier required' occurs after SSO login, "
                    "the server's Django CACHES backend is likely LocMemCache. "
                    "Switch to Redis/Memcached so all workers share the sso_cv_{state} cache key."
                ),
                issue_key="code_verifier_required",
            )
    return None


def hint_no_pkce_spa_fail(results: List[CheckResult]) -> Optional[Hint]:
    """If PKCE missing, Okta SPA app will reject the request."""
    for r in results:
        if r.name == "Auth URL has PKCE" and not r.passed:
            return Hint(
                "WARN",
                (
                    "Auth URL missing code_challenge — server is NOT using PKCE. "
                    "If IdP is Okta configured as SPA, token exchange will fail."
                ),
            )
    return None


def hint_state_invalid(results: List[CheckResult]) -> Optional[Hint]:
    """If token poll returns quickly, state may not be stored."""
    for r in results:
        if r.name == "Token poll endpoint" and r.passed:
            body = r.data.get("response", {})
            msg = str(body).lower()
            if "invalid" in msg and r.duration_ms is not None and r.duration_ms < 200:
                return Hint(
                    "INFO",
                    (
                        "Token poll returned 'state is invalid' quickly. "
                        "This is expected before SSO login completes. "
                        "If it persists after login, check server-side cache/worker configuration."
                    ),
                    issue_key="state_invalid_immediately",
                )
    return None


def hint_redirect_uri_mismatch(results: List[CheckResult]) -> Optional[Hint]:
    """Warn about redirect_uri hostname mismatch."""
    for r in results:
        if r.name == "Auth URL redirect_uri" and not r.passed:
            return Hint(
                "WARN",
                (
                    f"redirect_uri issue: {r.detail}. "
                    "Check reverse proxy / load balancer configuration."
                ),
            )
    return None


def hint_idp_unreachable(results: List[CheckResult]) -> Optional[Hint]:
    for r in results:
        if r.name == "IdP domain reachable" and not r.passed:
            return Hint(
                "WARN",
                f"IdP domain unreachable: {r.detail}. Check DNS and firewall rules.",
            )
    return None


def hint_sso_not_configured(results: List[CheckResult]) -> Optional[Hint]:
    for r in results:
        if r.name == "SSO login endpoint" and not r.passed:
            return Hint(
                "WARN",
                (
                    f"SSO endpoint error: {r.detail}. "
                    "SSO may not be configured on this server. "
                    "Check Nexus admin SSO provider settings."
                ),
            )
    return None


def hint_use_nonblocking(results: List[CheckResult]) -> Optional[Hint]:
    """Always recommend non-blocking mode for Databricks."""
    return Hint(
        "INFO",
        (
            "For Databricks notebooks, use sso_timeout=None (non-blocking mode). "
            "Call graphistry.sso_get_token() in a separate cell after completing SSO login."
        ),
        issue_key="sso_timeout_race",
    )


HINT_RULES: List[HintRuleFn] = [
    hint_pkce_cache_issue,
    hint_no_pkce_spa_fail,
    hint_state_invalid,
    hint_redirect_uri_mismatch,
    hint_idp_unreachable,
    hint_sso_not_configured,
    hint_use_nonblocking,
]


def generate_hints(results: List[CheckResult]) -> List[Hint]:
    hints = []
    for rule in HINT_RULES:
        h = rule(results)
        if h is not None:
            hints.append(h)
    return hints


# ---------------------------------------------------------------------------
# Main diagnostic runner
# ---------------------------------------------------------------------------

def run_diagnostic(
    server: str,
    protocol: str = "https",
    org_name: Optional[str] = None,
    idp_name: Optional[str] = None,
    output_json: bool = False,
) -> Dict[str, Any]:
    """Run all SSO diagnostic checks and return a report dict.

    Args:
        server: Graphistry server hostname (e.g. "graphistry-dev.grph.xyz").
        protocol: "https" or "http". Default "https".
        org_name: Optional organization name for org-scoped SSO.
        idp_name: Optional IdP name.
        output_json: If True, print JSON to stdout instead of text.

    Returns:
        Report dict with keys: version, server, results, hints, summary.
    """
    base_url = build_base_url(server, protocol)
    results: List[CheckResult] = []

    # ---- Check 1: Server reachable ----
    r1 = check_server_reachable(base_url)
    results.append(r1)

    if not r1.passed:
        # Cannot proceed without server
        hints = generate_hints(results)
        return _build_report(server, protocol, org_name, idp_name, results, hints, output_json)

    # ---- Check 2: SSO login endpoint ----
    r2 = check_sso_login_endpoint(base_url, org_name, idp_name)
    results.append(r2)

    auth_url = r2.data.get("auth_url", "")
    state = r2.data.get("state", "")

    if not r2.passed or not auth_url:
        hints = generate_hints(results)
        return _build_report(server, protocol, org_name, idp_name, results, hints, output_json)

    # ---- Checks 3-7: Auth URL analysis ----
    results.append(check_auth_url_pkce(auth_url))
    results.append(check_auth_url_client_id(auth_url))
    results.append(check_auth_url_redirect_uri(auth_url, server))
    results.append(check_auth_url_scopes(auth_url))
    results.append(check_auth_url_response_type(auth_url))

    # ---- Check 8: IdP reachable ----
    results.append(check_idp_reachable(auth_url))

    # ---- Check 9: Token poll ----
    if state:
        results.append(check_token_poll(base_url, state))

    # ---- Generate hints ----
    hints = generate_hints(results)

    return _build_report(server, protocol, org_name, idp_name, results, hints, output_json)


def _build_report(
    server: str,
    protocol: str,
    org_name: Optional[str],
    idp_name: Optional[str],
    results: List[CheckResult],
    hints: List[Hint],
    output_json: bool,
) -> Dict[str, Any]:
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    report: Dict[str, Any] = {
        "version": DIAGNOSE_SSO_VERSION,
        "server": f"{protocol}://{server}",
        "org_name": org_name,
        "idp_name": idp_name,
        "results": [r.to_dict() for r in results],
        "hints": [h.to_dict() for h in hints],
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "all_passed": failed == 0,
        },
    }

    if output_json:
        print(json.dumps(report, indent=2))
    else:
        _print_text_report(server, protocol, org_name, idp_name, results, hints, passed, failed)

    return report


def _print_text_report(
    server: str,
    protocol: str,
    org_name: Optional[str],
    idp_name: Optional[str],
    results: List[CheckResult],
    hints: List[Hint],
    passed: int,
    failed: int,
) -> None:
    print()
    print("=" * 50)
    print(" Graphistry SSO Diagnostic Report")
    print("=" * 50)
    print(f"  Version:  {DIAGNOSE_SSO_VERSION}")
    print(f"  Server:   {protocol}://{server}")
    if org_name:
        print(f"  Org:      {org_name}")
    if idp_name:
        print(f"  IdP:      {idp_name}")
    print("-" * 50)
    print()

    for r in results:
        print(f"  {r}")
    print()

    if hints:
        print("=" * 50)
        print(" Server-Side Hints")
        print("=" * 50)
        for h in hints:
            for i, line in enumerate(str(h).split("\n")):
                if i == 0:
                    print(f"  {line}")
                else:
                    print(f"  {line}")
            print()

    print("-" * 50)
    print(f"  Summary: {passed} passed, {failed} failed out of {passed + failed} checks")
    if failed == 0:
        print("  All client-side checks passed.")
    print("=" * 50)
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Graphistry SSO Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment variables:\n"
            "  GRAPHISTRY_SERVER    Server hostname (default: obsidian-tc.grph.xyz)\n"
            "  GRAPHISTRY_PROTOCOL  Protocol (default: https)\n"
            "\n"
            "Examples:\n"
            "  python diagnose_sso.py\n"
            "  python diagnose_sso.py --server graphistry-dev.grph.xyz\n"
            "  python diagnose_sso.py --server my-server.com --org-name my-org --json\n"
            "  GRAPHISTRY_SERVER=localhost GRAPHISTRY_PROTOCOL=http python diagnose_sso.py\n"
        ),
    )
    parser.add_argument("--server", default=DEFAULT_SERVER, help=f"Graphistry server hostname (default: {DEFAULT_SERVER})")
    parser.add_argument("--protocol", default=DEFAULT_PROTOCOL, help=f"Protocol (default: {DEFAULT_PROTOCOL})")
    parser.add_argument("--org-name", default=None, help="Organization name for org-scoped SSO")
    parser.add_argument("--idp-name", default=None, help="IdP name for IdP-specific SSO")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output JSON report")

    args = parser.parse_args()

    report = run_diagnostic(
        server=args.server,
        protocol=args.protocol,
        org_name=args.org_name,
        idp_name=args.idp_name,
        output_json=args.output_json,
    )

    # Exit with non-zero if any checks failed
    if not report["summary"]["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
