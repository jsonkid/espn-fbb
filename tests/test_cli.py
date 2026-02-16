from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from espn_fbb.cache import JsonCache
from espn_fbb.cli import app

runner = CliRunner()


LEAGUE_PAYLOAD = {
    "status": {"currentMatchupPeriod": 5, "currentScoringPeriod": 80},
    "schedule": [
        {
            "matchupPeriodId": 5,
            "home": {
                "teamId": 4,
                "cumulativeScore": {
                    "scoreByStat": {"19": 0.45, "20": 0.8, "17": 40, "6": 200, "3": 150, "2": 30, "1": 15, "11": 80, "0": 700}
                },
            },
            "away": {
                "teamId": 7,
                "cumulativeScore": {
                    "scoreByStat": {"19": 0.44, "20": 0.79, "17": 38, "6": 190, "3": 140, "2": 27, "1": 10, "11": 90, "0": 660}
                },
            },
        }
    ],
    "teams": [
        {"id": 4, "roster": {"entries": []}},
        {"id": 7, "roster": {"entries": []}},
    ],
}

SCHEDULE_PAYLOAD = {"proTeams": []}


def _write_config(path: Path) -> None:
    path.write_text(
        """
league_id = "123"
team_id = "4"
season = 2026
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_recap_outputs_json(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "config.toml"
    _write_config(cfg)

    def fake_get_league(self, *args, **kwargs):
        return LEAGUE_PAYLOAD

    monkeypatch.setattr("espn_fbb.cli.JsonCache", lambda: JsonCache(tmp_path))
    monkeypatch.setattr("espn_fbb.fetch.ESPNClient.get_league", fake_get_league)

    result = runner.invoke(app, ["recap", "--config-path", str(cfg)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["league_id"] == "123"
    assert "categories" in payload


def test_matchup_preview_outputs_json(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "config.toml"
    _write_config(cfg)

    def fake_get_league(self, *args, **kwargs):
        return LEAGUE_PAYLOAD

    def fake_get_schedule(self, *args, **kwargs):
        return SCHEDULE_PAYLOAD

    monkeypatch.setattr("espn_fbb.cli.JsonCache", lambda: JsonCache(tmp_path))
    monkeypatch.setattr("espn_fbb.fetch.ESPNClient.get_league", fake_get_league)
    monkeypatch.setattr("espn_fbb.fetch.ESPNClient.get_pro_team_schedules", fake_get_schedule)

    result = runner.invoke(app, ["matchup", "preview", "--config-path", str(cfg)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["league_id"] == "123"
    assert payload["schema_version"] == "2.0"
    assert "outlook" in payload


def test_matchup_outlook_outputs_json(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "config.toml"
    _write_config(cfg)

    def fake_get_league(self, *args, **kwargs):
        return LEAGUE_PAYLOAD

    def fake_get_schedule(self, *args, **kwargs):
        return SCHEDULE_PAYLOAD

    monkeypatch.setattr("espn_fbb.cli.JsonCache", lambda: JsonCache(tmp_path))
    monkeypatch.setattr("espn_fbb.fetch.ESPNClient.get_league", fake_get_league)
    monkeypatch.setattr("espn_fbb.fetch.ESPNClient.get_pro_team_schedules", fake_get_schedule)

    result = runner.invoke(app, ["matchup", "outlook", "--config-path", str(cfg)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["league_id"] == "123"
    assert payload["schema_version"] == "2.0"
    assert "games_remaining" in payload
