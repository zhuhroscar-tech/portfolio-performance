"""Tests for the Schwab OAuth client. All network calls are mocked via
monkeypatching urllib.request.urlopen -- these tests require no real
Schwab credentials and make no real network calls.
"""
from __future__ import annotations

import json
from datetime import date
from io import BytesIO
from unittest.mock import patch

import pytest

from engine.providers import schwab_api


def test_build_authorization_url_contains_client_id_and_redirect():
    url = schwab_api.build_authorization_url("MY_APP_KEY", "https://127.0.0.1:8182")
    assert url.startswith("https://api.schwabapi.com/v1/oauth/authorize?")
    assert "client_id=MY_APP_KEY" in url
    assert "redirect_uri=https%3A%2F%2F127.0.0.1%3A8182" in url


def test_extract_code_from_redirect_url():
    redirected = "https://127.0.0.1:8182/?code=SOME_CODE_VALUE&session=abc123"
    assert schwab_api.extract_code_from_redirect(redirected) == "SOME_CODE_VALUE"


def test_extract_code_from_redirect_url_missing_code_raises():
    with pytest.raises(ValueError, match="No 'code' query parameter"):
        schwab_api.extract_code_from_redirect("https://127.0.0.1:8182/?session=abc123")


class _FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_exchange_code_for_tokens_posts_correct_grant_type():
    captured = {}

    def fake_urlopen(req, timeout=30):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.headers)
        captured["body"] = req.data.decode("utf-8")
        return _FakeResponse(
            {
                "expires_in": 1800,
                "token_type": "Bearer",
                "scope": "api",
                "refresh_token": "REFRESH123",
                "access_token": "ACCESS123",
            }
        )

    with patch("urllib.request.urlopen", fake_urlopen):
        tokens = schwab_api.exchange_code_for_tokens(
            "KEY", "SECRET", "AUTHCODE", "https://127.0.0.1:8182"
        )

    assert tokens["refresh_token"] == "REFRESH123"
    assert tokens["access_token"] == "ACCESS123"
    assert captured["url"] == schwab_api.TOKEN_URL
    assert "grant_type=authorization_code" in captured["body"]
    assert "code=AUTHCODE" in captured["body"]
    assert captured["headers"]["Authorization"].startswith("Basic ")


def test_refresh_access_token_posts_correct_grant_type():
    def fake_urlopen(req, timeout=30):
        assert "grant_type=refresh_token" in req.data.decode("utf-8")
        assert "refresh_token=OLDREFRESH" in req.data.decode("utf-8")
        return _FakeResponse(
            {"access_token": "NEWACCESS", "refresh_token": "NEWREFRESH", "expires_in": 1800}
        )

    with patch("urllib.request.urlopen", fake_urlopen):
        tokens = schwab_api.refresh_access_token("KEY", "SECRET", "OLDREFRESH")

    assert tokens["access_token"] == "NEWACCESS"
    assert tokens["refresh_token"] == "NEWREFRESH"


def test_fetch_snapshot_sums_multiple_linked_accounts():
    fake_accounts = [
        {
            "securitiesAccount": {
                "currentBalances": {"liquidationValue": 100000.0, "cashBalance": 5000.0}
            }
        },
        {
            "securitiesAccount": {
                "currentBalances": {"liquidationValue": 25000.0, "cashBalance": 1000.0}
            }
        },
    ]

    def fake_urlopen(req, timeout=30):
        assert req.headers["Authorization"] == "Bearer ACCESS_TOKEN_VALUE"
        return _FakeResponse(fake_accounts)

    with patch("urllib.request.urlopen", fake_urlopen):
        snap = schwab_api.fetch_snapshot("ACCESS_TOKEN_VALUE", as_of=date(2026, 9, 12))

    assert snap.total_equity == 125000.0
    assert snap.cash == 6000.0
    assert snap.source == "schwab"
    assert snap.as_of == date(2026, 9, 12)


def test_fetch_snapshot_raises_on_empty_account_list():
    def fake_urlopen(req, timeout=30):
        return _FakeResponse([])

    with patch("urllib.request.urlopen", fake_urlopen):
        with pytest.raises(RuntimeError, match="empty or not a list"):
            schwab_api.fetch_snapshot("ACCESS_TOKEN_VALUE")
