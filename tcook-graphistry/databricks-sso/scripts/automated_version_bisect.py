#!/usr/bin/env python3
"""
Automated version bisect: test pygraphistry plot upload across versions.

Gets a JWT token once via SSO (manual browser click), then tests plot()
across multiple pygraphistry versions using that token. No repeated logins.

Usage:
    # Interactive: does SSO once, then tests all versions
    python scripts/automated_version_bisect.py

    # With existing token (skip SSO entirely):
    python scripts/automated_version_bisect.py --token <JWT>

    # Custom server:
    python scripts/automated_version_bisect.py --server obsidian-tc.grph.xyz
"""

import argparse
import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests required: pip install requests")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# Versions to test: known-good → boundary → breaking → client-reported
VERSIONS = ["0.44.1", "0.45.9", "0.45.10", "0.46.0", "0.47.0", "0.50.5", "0.50.6"]


def obtain_token_via_sso(server: str, protocol: str):
    """
    Initiate SSO, open browser for user login, poll for JWT.
    User clicks ONE link, and we get a reusable token.
    """
    base = f"{protocol}://{server}"
    url = f"{base}/api/v2/g/sso/oidc/login/"

    print("\n[SSO] Initiating SSO login...")
    resp = requests.post(url, json={}, timeout=15)
    if resp.status_code != 200:
        sys.exit(f"SSO initiate failed: HTTP {resp.status_code} - {resp.text[:200]}")

    data = resp.json()
    state = data.get("state")
    auth_url = data.get("auth_url")

    if not state or not auth_url:
        sys.exit(f"SSO response missing state/auth_url: {data}")

    print(f"[SSO] State: {state[:20]}...")
    print(f"[SSO] Opening browser for SSO login...")
    print(f"[SSO] URL: {auth_url[:100]}...")
    print()

    # Open browser
    webbrowser.open(auth_url)

    print("[SSO] Complete login in browser, then return here.")
    print("[SSO] Polling for JWT token...", end="", flush=True)

    # Poll for JWT
    poll_url = f"{base}/api/v2/o/sso/oidc/jwt/{state}/"
    start = time.time()
    timeout = 120

    while time.time() - start < timeout:
        try:
            r = requests.get(poll_url, timeout=10)
            d = r.json()
            if d.get("success") and d.get("data", {}).get("token"):
                token = d["data"]["token"]
                print(f" OK!")
                print(f"[SSO] Token obtained: {token[:30]}...")
                return token
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(3)

    sys.exit(f"\n[SSO] Timeout after {timeout}s waiting for JWT.")


def verify_token(server: str, protocol: str, token: str) -> bool:
    """Verify a JWT token is valid."""
    url = f"{protocol}://{server}/api/v2/auth/token/verify/"
    try:
        resp = requests.post(url, json={"token": token}, timeout=10)
        return 200 <= resp.status_code < 300
    except Exception:
        return False


def test_plot_in_venv(version: str, token: str, server: str, protocol: str):
    """
    Install graphistry in a venv and test plot upload using the JWT token.
    Returns dict with results.
    """
    # Find or create venv
    venv_dir = PROJECT_DIR / f"venv-{version}"
    if not venv_dir.exists():
        venv_dir = PROJECT_DIR / f"venv-bisect-{version}"

    if not venv_dir.exists():
        print(f"    Creating venv for {version}...", end="", flush=True)
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
        )
        r = subprocess.run(
            [str(venv_dir / "bin" / "pip"), "install", "-q",
             f"graphistry=={version}", "pandas", "pytz", "pyarrow"],
            capture_output=True, text=True, timeout=180,
        )
        if r.returncode != 0:
            return {"ok": False, "error": f"pip install failed: {r.stderr[:200]}"}
        print(" done")

    python = str(venv_dir / "bin" / "python")

    # Test 1: SSO sso_get_token behavior (static check)
    sso_check_code = '''
import json, inspect
try:
    from graphistry.arrow_uploader import ArrowUploader
    from graphistry.client_session import ClientSession, ApiVersion

    src = inspect.getsource(ArrowUploader.sso_get_token)
    active_org_required = "raise Exception" in src and "active_organization" in src
    has_switch = hasattr(ArrowUploader, "_switch_org")

    cs = ClientSession()
    result = {
        "active_org_required": active_org_required,
        "switch_org": has_switch,
        "api_version": str(ApiVersion),
        "api_default": cs.api_version,
    }
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"error": str(e)}))
'''

    # Test 2: Actual plot upload with token
    # Escape the token for embedding in the f-string
    escaped_token = token.replace("\\", "\\\\").replace('"', '\\"')
    plot_code = f'''
import json, sys
try:
    import graphistry
    graphistry.register(api=3, protocol="{protocol}", server="{server}", token="{escaped_token}")

    # Verify token works
    valid = graphistry.verify_token()
    if not valid:
        print(json.dumps({{"ok": False, "error": "Token verification failed"}}))
        sys.exit(0)

    import pandas as pd
    edges = pd.DataFrame({{"s": ["a","b","c","d","e"], "d": ["b","c","d","e","a"]}})
    g = graphistry.edges(edges, "s", "d")
    url = g.plot(render=False)

    # Check internal state
    session = graphistry.PyGraphistry._config
    org = getattr(session, "org_name", None)

    print(json.dumps({{
        "ok": True,
        "url": url,
        "version": graphistry.__version__,
        "org_name": org,
        "token_valid": True,
    }}))
except Exception as e:
    import traceback
    print(json.dumps({{
        "ok": False,
        "error": str(e),
        "traceback": traceback.format_exc()
    }}))
'''

    result = {"version": version}

    # Run static check
    try:
        proc = subprocess.run(
            [python, "-c", sso_check_code],
            capture_output=True, text=True, timeout=30,
        )
        if proc.stdout.strip():
            result["static"] = json.loads(proc.stdout.strip())
        else:
            result["static"] = {"error": proc.stderr[:200]}
    except Exception as e:
        result["static"] = {"error": str(e)}

    # Run plot test
    try:
        proc = subprocess.run(
            [python, "-c", plot_code],
            capture_output=True, text=True, timeout=60,
        )
        if proc.stdout.strip():
            plot_result = json.loads(proc.stdout.strip())
            result.update(plot_result)
        else:
            result["ok"] = False
            result["error"] = proc.stderr[:300]
    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Automated pygraphistry version bisect")
    parser.add_argument("--token", default=None, help="Existing JWT token (skip SSO)")
    parser.add_argument("--server", default="graphistry-dev.grph.xyz", help="Graphistry server")
    parser.add_argument("--protocol", default="https")
    parser.add_argument("--versions", default=None, help="Comma-separated version list")
    args = parser.parse_args()

    server = args.server
    protocol = args.protocol
    versions = args.versions.split(",") if args.versions else VERSIONS

    print("=" * 70)
    print("  pygraphistry Version Bisect (Automated)")
    print(f"  Server:   {protocol}://{server}")
    print(f"  Versions: {', '.join(versions)}")
    print("=" * 70)

    # Get token
    token = args.token
    if not token:
        token = obtain_token_via_sso(server, protocol)

    # Verify token
    print(f"\n[Token] Verifying JWT...", end=" ")
    if verify_token(server, protocol, token):
        print("valid")
    else:
        print("INVALID — proceeding anyway (may fail)")

    # Test each version
    all_results = []
    for version in versions:
        print(f"\n{'='*70}")
        print(f"  graphistry=={version}")
        print(f"{'='*70}")

        result = test_plot_in_venv(version, token, server, protocol)
        all_results.append(result)

        static = result.get("static", {})
        ok = result.get("ok", False)
        url = result.get("url", "")
        err = result.get("error", "")

        print(f"    Static: active_org_required={static.get('active_org_required', '?')}, "
              f"switch_org={static.get('switch_org', '?')}, "
              f"api={static.get('api_default', '?')}")

        if ok:
            print(f"    Plot:   OK — {url[:80]}")
        else:
            print(f"    Plot:   FAIL — {err[:80]}")

    # Summary
    print(f"\n\n{'='*70}")
    print("  RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"\n{'Version':<12} {'Plot':<8} {'active_org':<15} {'switch_org':<12} {'API':<12} {'Error'}")
    print("-" * 85)

    for r in all_results:
        v = r["version"]
        ok = "OK" if r.get("ok") else "FAIL"
        s = r.get("static", {})
        ao = "required" if s.get("active_org_required") else "optional"
        sw = str(s.get("switch_org", "?"))
        api = str(s.get("api_default", "?"))
        err = r.get("error", "")[:30]
        print(f"{v:<12} {ok:<8} {ao:<15} {sw:<12} {api:<12} {err}")

    print(f"\n{'='*70}")
    print("  ANALYSIS")
    print(f"{'='*70}")

    # Find the boundary
    last_ok = None
    first_fail = None
    for r in all_results:
        if r.get("ok"):
            last_ok = r["version"]
        elif first_fail is None:
            first_fail = r["version"]

    if last_ok and first_fail:
        print(f"\n  Last working version:  {last_ok}")
        print(f"  First broken version:  {first_fail}")
    elif last_ok:
        print(f"\n  All tested versions work. Last tested: {last_ok}")
    else:
        print(f"\n  All tested versions fail. First tested: {all_results[0]['version']}")

    # Save results
    results_file = PROJECT_DIR / "notebooks" / "bisect_results.json"
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Results saved to {results_file}")


if __name__ == "__main__":
    main()
