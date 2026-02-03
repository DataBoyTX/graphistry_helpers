#!/usr/bin/env python3
"""
Push a Jupyter notebook to a Databricks workspace.

Reads DATABRICKS_HOST, DATABRICKS_PAT, and optionally DATABRICKS_NOTEBOOK_PATH from .env.

Usage:
    python scripts/push_notebook.py notebooks/test_privacy_iframe.ipynb
    python scripts/push_notebook.py notebooks/test_privacy_iframe.ipynb \
        --remote-path /Workspace/Users/tcook@graphistry.com/SSO-register/DBT/claude/test_privacy_iframe
"""

import argparse
import base64
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests is required: pip install requests")

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("python-dotenv is required: pip install python-dotenv")


def find_env_file():
    """Walk up from script location to find .env."""
    d = Path(__file__).resolve().parent
    while d != d.parent:
        env = d / ".env"
        if env.exists():
            return env
        d = d.parent
    return None


def push_notebook(local_path: str, remote_path: str, host: str, token: str):
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    url = f"https://{host}/api/2.0/workspace/import"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "path": remote_path,
            "format": "JUPYTER",
            "language": "PYTHON",
            "content": content,
            "overwrite": True,
        },
    )

    if resp.status_code == 200:
        print(f"Uploaded: {local_path} -> {remote_path}")
        print(f"  Host: {host}")
    else:
        print(f"Upload failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Push a notebook to Databricks")
    parser.add_argument("notebook", help="Local .ipynb file path")
    parser.add_argument(
        "--remote-path",
        default=None,
        help="Full Databricks workspace path (default: DATABRICKS_NOTEBOOK_PATH + filename stem)",
    )
    args = parser.parse_args()

    env_file = find_env_file()
    if env_file:
        load_dotenv(env_file)
        print(f"Loaded .env from {env_file}")

    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_PAT")

    if not host or not token:
        sys.exit("DATABRICKS_HOST and DATABRICKS_PAT must be set in .env or environment")

    local_path = Path(args.notebook)
    if not local_path.exists():
        sys.exit(f"File not found: {local_path}")

    if args.remote_path:
        remote_path = args.remote_path
    else:
        base_dir = os.environ.get(
            "DATABRICKS_NOTEBOOK_PATH",
            "/Workspace/Users/tcook@graphistry.com/SSO-register/DBT/claude/",
        )
        remote_path = base_dir.rstrip("/") + "/" + local_path.stem

    push_notebook(str(local_path), remote_path, host, token)


if __name__ == "__main__":
    main()
