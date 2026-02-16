from __future__ import annotations

from pathlib import Path

import pytest

from espn_fbb.cache import JsonCache
from espn_fbb.fetch import AuthError, ESPNClient, RequestBudget, RequestLimitError


class DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_fallback_on_403(monkeypatch, tmp_path: Path):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if "fantasy.espn.com" in url and "lm-api-reads" not in url:
            return DummyResponse(403, {})
        return DummyResponse(200, {"ok": True})

    monkeypatch.setattr("requests.get", fake_get)
    client = ESPNClient(league_id="1", season=2026, cache=JsonCache(tmp_path))

    payload = client.get_league(["mTeam"], use_cache=False)
    assert payload["ok"] is True
    assert len(calls) == 2
    assert "fantasy.espn.com" in calls[0]
    assert "lm-api-reads" in calls[1]


def test_auth_error_after_fallback_403(monkeypatch, tmp_path: Path):
    def fake_get(url, **kwargs):
        return DummyResponse(403, {})

    monkeypatch.setattr("requests.get", fake_get)
    client = ESPNClient(league_id="1", season=2026, cache=JsonCache(tmp_path))

    with pytest.raises(AuthError):
        client.get_league(["mTeam"], use_cache=False)


def test_request_budget_enforced(tmp_path: Path):
    client = ESPNClient(
        league_id="1",
        season=2026,
        cache=JsonCache(tmp_path),
        budget=RequestBudget(max_espn_requests=0),
    )

    with pytest.raises(RequestLimitError):
        client.get_league(["mTeam"], use_cache=True)


def test_cache_hit_skips_network(monkeypatch, tmp_path: Path):
    calls = {"count": 0}

    def fake_get(url, **kwargs):
        calls["count"] += 1
        return DummyResponse(200, {"value": 1})

    monkeypatch.setattr("requests.get", fake_get)
    client = ESPNClient(league_id="1", season=2026, cache=JsonCache(tmp_path))

    first = client.get_league(["mTeam"], use_cache=True)
    second = client.get_league(["mTeam"], use_cache=True)

    assert first == second
    assert calls["count"] == 1
