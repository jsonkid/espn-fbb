from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import requests

from espn_fbb.cache import JsonCache


PRIMARY_BASE = "https://fantasy.espn.com/apis/v3/games/fba"
FALLBACK_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba"


class ESPNError(RuntimeError):
    """Base ESPN client error."""


class AuthError(ESPNError):
    """Raised when ESPN authentication fails."""


class RequestLimitError(ESPNError):
    """Raised when command request budget is exceeded."""


@dataclass
class RequestBudget:
    max_espn_requests: int = 2
    max_schedule_requests: int = 1
    espn_requests: int = 0
    schedule_requests: int = 0

    def consume_espn(self) -> None:
        self.espn_requests += 1
        if self.espn_requests > self.max_espn_requests:
            raise RequestLimitError("Exceeded ESPN request budget")

    def consume_schedule(self) -> None:
        self.schedule_requests += 1
        if self.schedule_requests > self.max_schedule_requests:
            raise RequestLimitError("Exceeded schedule request budget")


@dataclass
class ESPNClient:
    league_id: str
    season: int
    espn_s2: str | None = None
    swid: str | None = None
    cache: JsonCache = field(default_factory=JsonCache)
    timeout_seconds: int = 20
    budget: RequestBudget = field(default_factory=RequestBudget)

    def _cookies(self) -> dict[str, str]:
        cookies: dict[str, str] = {}
        if self.espn_s2:
            cookies["espn_s2"] = self.espn_s2
        if self.swid:
            cookies["SWID"] = self.swid
        return cookies

    def _cache_key(self, endpoint: str, params: list[tuple[str, Any]], filter_header: dict[str, Any] | None) -> str:
        return json.dumps(
            {
                "league_id": self.league_id,
                "season": self.season,
                "endpoint": endpoint,
                "params": params,
                "filter": filter_header,
            },
            sort_keys=True,
        )

    def _request_with_fallback(
        self,
        endpoint: str,
        params: list[tuple[str, Any]],
        filter_header: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if filter_header:
            headers["x-fantasy-filter"] = json.dumps(filter_header, separators=(",", ":"))

        bases = [PRIMARY_BASE, FALLBACK_BASE]
        last_response: requests.Response | None = None
        for idx, base in enumerate(bases):
            url = f"{base}{endpoint}"
            response = requests.get(
                url,
                params=params,
                headers=headers,
                cookies=self._cookies(),
                timeout=self.timeout_seconds,
            )
            last_response = response
            if response.status_code == 403 and idx == 0:
                continue
            break

        if last_response is None:
            raise ESPNError("No response from ESPN")
        if last_response.status_code in (401, 403):
            raise AuthError(f"Authentication failed ({last_response.status_code})")
        if last_response.status_code >= 400:
            raise ESPNError(f"ESPN API error ({last_response.status_code})")

        try:
            return last_response.json()
        except ValueError as exc:
            raise ESPNError("Invalid JSON response from ESPN") from exc

    def get_league(
        self,
        views: list[str],
        *,
        scoring_period_id: int | None = None,
        matchup_period_id: int | None = None,
        use_cache: bool = True,
        cache_ttl_seconds: int = 3 * 60 * 60,
    ) -> dict[str, Any]:
        self.budget.consume_espn()
        endpoint = f"/seasons/{self.season}/segments/0/leagues/{self.league_id}"
        params: list[tuple[str, Any]] = [("view", view) for view in views]
        if scoring_period_id is not None:
            params.append(("scoringPeriodId", scoring_period_id))

        filter_header = None
        if matchup_period_id is not None:
            filter_header = {
                "schedule": {
                    "filterMatchupPeriodIds": {
                        "value": [matchup_period_id],
                    }
                }
            }

        key = self._cache_key(endpoint, params, filter_header)
        if use_cache:
            cached = self.cache.get(key, ttl_seconds=cache_ttl_seconds)
            if cached is not None:
                return cached

        payload = self._request_with_fallback(endpoint, params, filter_header)
        if use_cache:
            self.cache.set(key, payload)
        return payload

    def get_pro_team_schedules(
        self,
        *,
        use_cache: bool = True,
        cache_ttl_seconds: int = 24 * 60 * 60,
    ) -> dict[str, Any]:
        self.budget.consume_schedule()
        endpoint = f"/seasons/{self.season}"
        params = [("view", "proTeamSchedules_wl")]

        key = self._cache_key(endpoint, params, None)
        if use_cache:
            cached = self.cache.get(key, ttl_seconds=cache_ttl_seconds)
            if cached is not None:
                return cached

        payload = self._request_with_fallback(endpoint, params)
        if use_cache:
            self.cache.set(key, payload)
        return payload
