from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli


class ConfigError(ValueError):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True)
class AppConfig:
    league_id: str
    team_id: int
    season: int
    espn_s2: str | None = None
    swid: str | None = None


DEFAULT_CONFIG_PATH = Path("~/.config/espn-fbb/config.toml").expanduser()


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("rb") as fh:
        return tomli.load(fh)


def load_config(
    config_path: Path | None = None,
    league_id: str | None = None,
    team_id: int | None = None,
    season: int | None = None,
) -> AppConfig:
    path = config_path or DEFAULT_CONFIG_PATH
    data = _read_toml(path)

    final_league_id = str(league_id or data.get("league_id", "")).strip()
    if not final_league_id:
        raise ConfigError("league_id is required")

    raw_team_id = team_id if team_id is not None else data.get("team_id")
    if raw_team_id is None:
        raise ConfigError("team_id is required")

    raw_season = season if season is not None else data.get("season")
    if raw_season is None:
        raise ConfigError("season is required")

    try:
        final_team_id = int(raw_team_id)
    except (TypeError, ValueError) as exc:
        raise ConfigError("team_id must be an integer") from exc

    try:
        final_season = int(raw_season)
    except (TypeError, ValueError) as exc:
        raise ConfigError("season must be an integer") from exc

    return AppConfig(
        league_id=final_league_id,
        team_id=final_team_id,
        season=final_season,
        espn_s2=data.get("espn_s2"),
        swid=data.get("swid"),
    )
