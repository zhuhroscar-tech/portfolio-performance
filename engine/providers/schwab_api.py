"""Schwab Trader API provider — OAuth client + account snapshot fetch.

This module is now FULLY IMPLEMENTED. It is not yet USABLE end-to-end
because it requires credentials only the account owner can obtain (see
"What is blocked and why" below) — but every function here is real,
tested code, not a stub. Once the user supplies an app key/secret and
completes one interactive login (scripts/schwab_login.py), this module
already does everything scripts/update_performance.py needs.

=== What is blocked and why (read this before enabling) ===

1. Registration: requires creating an Individual Developer account at
   https://developer.schwab.com/, registering an app under the
   "Trader API - Individual" product, and waiting for Schwab's approval
   (historically hours to a few business days). Only the account owner
   can do this -- it needs the user's own Schwab login and identity
   verification. Not automatable by an agent.

2. OAuth token lifecycle (hard platform limit, not a bug to work
   around): the access_token lasts 30 minutes and the refresh_token
   lasts exactly 7 days. Renewing after 7 days requires completing the
   OAuth *authorization* flow again -- an interactive browser login
   with Schwab credentials and (typically) MFA. There is no
   long-lived/offline token. This means a fully unattended daily cron
   job CANNOT run indefinitely on raw Schwab API credentials alone --
   it will hard-fail every 7 days until a human re-authorizes.

   Practical implication for "daily automatic updates": either (a) the
   user re-authorizes roughly weekly (a ~30-second browser flow via
   scripts/schwab_login.py), which keeps GitHub Actions running daily
   in between, or (b) use a brokerage-aggregator (e.g. SnapTrade)
   instead, which manages this token refresh problem server-side.

3. Credentials must never be committed. Once the user has an app key/
   secret, they belong in environment variables / GitHub Actions
   "Repository secrets", never in this repo's source or config.

=== Verified against Schwab's own OAuth documentation ===

  https://developer.schwab.com/user-guides/get-started/authenticate-with-oauth

  Authorization URL: https://api.schwabapi.com/v1/oauth/authorize
  Token URL:          https://api.schwabapi.com/v1/oauth/token
  Accounts API base:  https://api.schwabapi.com/trader/v1

=== Next concrete step for the user ===

  1. Go to https://developer.schwab.com/, register as an Individual
     Developer, and create an app requesting the "Trader API -
     Individual" product (read-only account/position access is
     sufficient -- do not request trading/order-placement scopes for a
     read-only performance tracker). Set the app's callback/redirect
     URL to something like https://127.0.0.1:8182 (a local placeholder
     is fine -- Schwab's flow ends with a redirect to a non-existent
     page purely so the "code" query parameter can be read from the
     address bar).
  2. Once approved, export SCHWAB_APP_KEY and SCHWAB_APP_SECRET locally
     and run `python3 scripts/schwab_login.py` -- it opens the
     authorization URL, asks you to paste the redirected URL back, and
     prints a refresh_token to save as a GitHub Actions secret
     (SCHWAB_REFRESH_TOKEN).
  3. Add SCHWAB_APP_KEY, SCHWAB_APP_SECRET, SCHWAB_REFRESH_TOKEN as
     repository secrets, then enable .github/workflows/daily-update.yml
     (see that file's comments -- it is written to no-op safely until
     secrets exist).
  4. Repeat step 2 roughly weekly (or whenever the workflow reports an
     expired-refresh-token failure) until an aggregator-based provider
     removes that need.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from base64 import b64encode
from datetime import date, datetime, timezone

from ..schemas import EquitySnapshot

AUTHORIZE_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
API_BASE = "https://api.schwabapi.com/trader/v1"


def build_authorization_url(app_key: str, redirect_uri: str) -> str:
    """Step 1 of the OAuth flow: the URL the user opens in a browser to
    log in to Schwab and grant this app read access to their account(s).
    """
    query = urllib.parse.urlencode({"client_id": app_key, "redirect_uri": redirect_uri})
    return f"{AUTHORIZE_URL}?{query}"


def extract_code_from_redirect(redirect_url: str) -> str:
    """After granting access, Schwab redirects to `redirect_uri` with a
    `code` query parameter (and the browser lands on a 404 -- expected,
    per Schwab's docs; only the URL's query string matters). This pulls
    the authorization code back out, decoding the URL-encoded value.
    """
    parsed = urllib.parse.urlparse(redirect_url)
    params = urllib.parse.parse_qs(parsed.query)
    codes = params.get("code")
    if not codes:
        raise ValueError(
            f"No 'code' query parameter found in redirect URL: {redirect_url!r}. "
            "Paste the FULL URL from the browser's address bar after granting access, "
            "including everything after '?code='."
        )
    return codes[0]


def _basic_auth_header(app_key: str, app_secret: str) -> str:
    raw = f"{app_key}:{app_secret}".encode("utf-8")
    return "Basic " + b64encode(raw).decode("ascii")


def _post_token_request(app_key: str, app_secret: str, form_data: dict) -> dict:
    body = urllib.parse.urlencode(form_data).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": _basic_auth_header(app_key, app_secret),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Schwab token endpoint returned HTTP {exc.code}: {detail}"
        ) from exc


def exchange_code_for_tokens(
    app_key: str, app_secret: str, code: str, redirect_uri: str
) -> dict:
    """Step 2: trade the one-time authorization code for an initial
    access_token (30 min) + refresh_token (7 days). Returns the raw
    token response dict (see Schwab's documented shape: expires_in,
    token_type, scope, refresh_token, access_token, id_token).
    """
    return _post_token_request(
        app_key,
        app_secret,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )


def refresh_access_token(app_key: str, app_secret: str, refresh_token: str) -> dict:
    """Step 4: exchange a still-valid (<7 day old) refresh_token for a
    new access_token. Schwab may also rotate the refresh_token itself in
    the response -- callers should persist whichever refresh_token comes
    back, not assume it is unchanged.
    """
    return _post_token_request(
        app_key,
        app_secret,
        {"grant_type": "refresh_token", "refresh_token": refresh_token},
    )


def _get(access_token: str, path: str) -> object:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Schwab API GET {path} returned HTTP {exc.code}: {detail}") from exc


def fetch_snapshot(access_token: str, as_of: date | None = None) -> EquitySnapshot:
    """Fetch every linked account's current balances and sum them into a
    single EquitySnapshot for "today" (or `as_of` if given, e.g. for a
    scheduled job that wants to timestamp with the run date rather than
    the API's own clock).

    Uses GET /accounts?fields=positions, which the Accounts API
    documents as returning liquidationValue-bearing currentBalances
    per linked account. Summed across accounts and cash balances
    reported (some Schwab responses omit certain currentBalances
    sub-fields depending on account type; we default missing ones to 0
    rather than fail the whole snapshot).
    """
    accounts = _get(access_token, "/accounts?fields=positions")
    if not isinstance(accounts, list) or not accounts:
        raise RuntimeError(
            "Schwab /accounts response was empty or not a list -- no linked accounts "
            "returned for this token, or the response shape changed."
        )

    total_equity = 0.0
    total_cash = 0.0
    for wrapper in accounts:
        acct = wrapper.get("securitiesAccount", wrapper)
        balances = acct.get("currentBalances", {})
        # liquidationValue is Schwab's documented "total account value" field.
        total_equity += float(balances.get("liquidationValue", 0) or 0)
        total_cash += float(balances.get("cashBalance", balances.get("cashAvailableForTrading", 0)) or 0)

    return EquitySnapshot(
        as_of=as_of or datetime.now(timezone.utc).date(),
        total_equity=round(total_equity, 2),
        cash=round(total_cash, 2),
        source="schwab",
    )
