#!/usr/bin/env python3
"""Interactive Schwab OAuth login: run this once (and again roughly every
7 days, whenever the refresh token expires) to produce a refresh_token
for the daily automated job to use.

This step is INTERACTIVE ON PURPOSE: Schwab's OAuth flow requires you to
log in through your own browser with your own Schwab credentials (and
MFA). No agent or script can complete this on your behalf -- that is a
deliberate security boundary, not a limitation of this tool.

Usage:
    export SCHWAB_APP_KEY=...      # from developer.schwab.com app registration
    export SCHWAB_APP_SECRET=...
    export SCHWAB_REDIRECT_URI=https://127.0.0.1:8182   # must match your app's registered callback
    python3 scripts/schwab_login.py

What happens:
    1. Prints an authorization URL. Open it in your browser and log in
       to Schwab, then select the account(s) to share and approve.
    2. Schwab redirects your browser to your app's callback URL. That
       page will likely show a 404 or "can't be reached" -- this is
       expected (see Schwab's own docs). What matters is the URL in
       your browser's address bar, which now contains a `code=...`
       query parameter.
    3. Paste that FULL URL back into this script when prompted.
    4. This script exchanges the code for an access_token + refresh_token
       and prints the refresh_token for you to save as a GitHub Actions
       repository secret named SCHWAB_REFRESH_TOKEN.

The refresh_token is valid for 7 days. Re-run this script whenever the
daily workflow reports it has expired.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.providers import schwab_api  # noqa: E402


def main() -> int:
    app_key = os.environ.get("SCHWAB_APP_KEY", "").strip()
    app_secret = os.environ.get("SCHWAB_APP_SECRET", "").strip()
    redirect_uri = os.environ.get("SCHWAB_REDIRECT_URI", "").strip()

    missing = [
        name
        for name, val in [
            ("SCHWAB_APP_KEY", app_key),
            ("SCHWAB_APP_SECRET", app_secret),
            ("SCHWAB_REDIRECT_URI", redirect_uri),
        ]
        if not val
    ]
    if missing:
        print(
            "error: missing required environment variable(s): " + ", ".join(missing),
            file=sys.stderr,
        )
        print(__doc__, file=sys.stderr)
        return 1

    auth_url = schwab_api.build_authorization_url(app_key, redirect_uri)
    print("\n1. Open this URL in your browser and log in to Schwab:\n")
    print(f"   {auth_url}\n")
    print("2. After granting access, your browser will land on a page that")
    print("   may show an error/404 -- that is expected. Copy the FULL URL")
    print("   from the address bar (it contains '?code=...').\n")

    redirected_url = input("3. Paste that full URL here: ").strip()
    try:
        code = schwab_api.extract_code_from_redirect(redirected_url)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        tokens = schwab_api.exchange_code_for_tokens(app_key, app_secret, code, redirect_uri)
    except RuntimeError as exc:
        print(f"error exchanging code for tokens: {exc}", file=sys.stderr)
        return 1

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print(f"error: no refresh_token in response: {tokens}", file=sys.stderr)
        return 1

    print("\nSuccess. Save this as the GitHub Actions repository secret")
    print("SCHWAB_REFRESH_TOKEN (Settings -> Secrets and variables -> Actions):\n")
    print(f"   {refresh_token}\n")
    print("This refresh token is valid for 7 days. Re-run this script when it expires.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
