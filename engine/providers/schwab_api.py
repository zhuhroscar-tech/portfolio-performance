"""Schwab Trader API provider — NOT YET USABLE. Blocked on user action.

This module documents the exact integration this project will use once
unblocked, so wiring it in later is a small change, not a redesign.

=== What is blocked and why (read this before enabling) ===

1. Registration: requires creating an Individual Developer account at
   https://developer.schwab.com/, registering an app under the
   "Trader API - Individual" product, and waiting for Schwab's approval
   (historically hours to a few business days). Only the account owner
   can do this -- it needs the user's own Schwab login and identity
   verification. Not automatable by an agent.

2. OAuth token lifecycle (hard platform limit, not a bug to work
   around): the access_token lasts ~30 minutes and the refresh_token
   lasts exactly 7 days. Renewing after 7 days requires completing the
   OAuth *authorization* flow again -- an interactive browser login
   with Schwab credentials and (typically) MFA. There is no
   long-lived/offline token. This means a fully unattended daily cron
   job CANNOT run indefinitely on raw Schwab API credentials alone --
   it will hard-fail every 7 days until a human re-authorizes.

   Practical implication for "daily automatic updates": either (a) the
   user re-authorizes roughly weekly (a 30-second browser click), which
   this module's `run_oauth_login()` will support once app credentials
   exist, or (b) use the SnapTrade provider instead, which manages this
   token refresh problem for the user.

3. Credentials must never be committed. Once the user has an app key/
   secret, they belong in environment variables consumed at runtime
   (e.g. via GitHub Actions "Repository secrets"), never in this repo's
   source or config.yaml.

=== What this module will do once unblocked ===

    fetch_snapshot(app_key: str, app_secret: str, refresh_token: str) -> EquitySnapshot

Calling GET /trader/v1/accounts/{accountNumber} (or the account-numbers
+ positions endpoints) for current total account value, then returning
it as a single EquitySnapshot for "today". A daily cron run then reads
one snapshot, appends it to the tracked history, and recomputes
performance -- exactly like manual_entry.py, just sourced from a live
API instead of a hand-maintained CSV.

=== Next concrete step for the user ===

  1. Go to https://developer.schwab.com/, register as an Individual
     Developer, and create an app requesting the "Trader API -
     Individual" product (read-only account/position access is
     sufficient -- do not request trading/order-placement scopes for a
     read-only performance tracker).
  2. Once approved, provide the app key + app secret (via a secret
     store / GitHub Actions secret, never pasted in chat) and this
     module will be completed and wired into scripts/update_performance.py.
"""
from __future__ import annotations


def fetch_snapshot(app_key: str, app_secret: str, refresh_token: str):
    """Not implemented yet -- see this module's docstring for exactly
    why (Schwab developer-app registration + weekly interactive OAuth
    re-auth, neither of which an agent can complete on the user's
    behalf) and the concrete next step to unblock it. Raising only when
    this is actually called (not at import time) keeps this module safe
    to import from tests and scripts that just check provider wiring.
    """
    raise NotImplementedError(
        "Schwab Trader API provider is not usable yet: it requires a Schwab "
        "Individual Developer app registration (an interactive step only the "
        "account owner can complete) and, on approval, an app key/secret "
        "supplied via environment variables. See this file's module "
        "docstring for the exact next step. Use engine.providers.manual_entry "
        "or engine.providers.realized_pnl in the meantime."
    )
