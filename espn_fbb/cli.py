from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import typer

from espn_fbb.analytics import build_outlook, build_preview, build_recap, build_snapshot
from espn_fbb.cache import JsonCache
from espn_fbb.config import ConfigError, load_config
from espn_fbb.fetch import AuthError, ESPNClient, ESPNError, RequestLimitError
from espn_fbb.utils import et_date_str, now_et

app = typer.Typer(add_completion=False, no_args_is_help=True)
matchup_app = typer.Typer(add_completion=False, no_args_is_help=True)
app.add_typer(matchup_app, name="matchup")


def _exit(code: int, message: str) -> None:
    typer.echo(json.dumps({"error": message}))
    raise typer.Exit(code=code)


@app.command()
def recap(
    league_id: str | None = typer.Option(None, "--league-id"),
    team_id: int | None = typer.Option(None, "--team-id"),
    season: int | None = typer.Option(None, "--season"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    config_path: Path | None = typer.Option(None, "--config-path", hidden=True),
) -> None:
    cache = JsonCache()

    try:
        cfg = load_config(config_path=config_path, league_id=league_id, team_id=team_id, season=season)
        client = ESPNClient(
            league_id=cfg.league_id,
            season=cfg.season,
            espn_s2=cfg.espn_s2,
            swid=cfg.swid,
            cache=cache,
        )

        views = ["mMatchupScore", "mScoreboard", "mTeam", "mRoster", "mSettings"]
        league = client.get_league(views=views, use_cache=not no_cache, cache_ttl_seconds=3 * 60 * 60)

        today = now_et()
        yesterday = today - timedelta(days=1)
        current_matchup = (league.get("status") or {}).get("currentMatchupPeriod", 1)
        if isinstance(current_matchup, list):
            current_matchup = current_matchup[0] if current_matchup else 1
        matchup_period_id = int(current_matchup)
        yesterday_key = cache.snapshot_key(cfg.league_id, cfg.team_id, matchup_period_id, et_date_str(yesterday))
        yesterday_snapshot = cache.get(yesterday_key, ttl_seconds=10 * 24 * 60 * 60)

        recap_model = build_recap(
            league_payload=league,
            team_id=cfg.team_id,
            league_id=cfg.league_id,
            yesterday_snapshot=yesterday_snapshot,
        )

        today_key = cache.snapshot_key(cfg.league_id, cfg.team_id, recap_model.matchup_period_id, et_date_str(today))
        cache.set(today_key, build_snapshot(recap_model.categories))
        cache.purge_old_snapshots(retention_days=10)

        typer.echo(recap_model.model_dump_json())
    except ConfigError as exc:
        _exit(2, str(exc))
    except AuthError as exc:
        _exit(3, str(exc))
    except (ESPNError, RequestLimitError) as exc:
        _exit(4, str(exc))
    except typer.Exit:
        raise
    except Exception as exc:  # pragma: no cover
        _exit(5, f"Unexpected runtime error: {exc}")


@matchup_app.command("preview")
def matchup_preview(
    league_id: str | None = typer.Option(None, "--league-id"),
    team_id: int | None = typer.Option(None, "--team-id"),
    season: int | None = typer.Option(None, "--season"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    config_path: Path | None = typer.Option(None, "--config-path", hidden=True),
) -> None:
    cache = JsonCache()

    try:
        cfg = load_config(config_path=config_path, league_id=league_id, team_id=team_id, season=season)
        client = ESPNClient(
            league_id=cfg.league_id,
            season=cfg.season,
            espn_s2=cfg.espn_s2,
            swid=cfg.swid,
            cache=cache,
        )

        views = ["mMatchupScore", "mScoreboard", "mTeam", "mRoster", "mSettings", "mMatchup"]
        league = client.get_league(views=views, use_cache=not no_cache, cache_ttl_seconds=3 * 60 * 60)
        schedule = client.get_pro_team_schedules(use_cache=not no_cache, cache_ttl_seconds=24 * 60 * 60)

        preview_model = build_preview(
            league_payload=league,
            schedule_payload=schedule,
            team_id=cfg.team_id,
            league_id=cfg.league_id,
            week="next",
        )

        typer.echo(preview_model.model_dump_json())
    except ConfigError as exc:
        _exit(2, str(exc))
    except AuthError as exc:
        _exit(3, str(exc))
    except (ESPNError, RequestLimitError) as exc:
        _exit(4, str(exc))
    except typer.Exit:
        raise
    except Exception as exc:  # pragma: no cover
        _exit(5, f"Unexpected runtime error: {exc}")


@matchup_app.command("outlook")
def matchup_outlook(
    league_id: str | None = typer.Option(None, "--league-id"),
    team_id: int | None = typer.Option(None, "--team-id"),
    season: int | None = typer.Option(None, "--season"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    config_path: Path | None = typer.Option(None, "--config-path", hidden=True),
) -> None:
    cache = JsonCache()

    try:
        cfg = load_config(config_path=config_path, league_id=league_id, team_id=team_id, season=season)
        client = ESPNClient(
            league_id=cfg.league_id,
            season=cfg.season,
            espn_s2=cfg.espn_s2,
            swid=cfg.swid,
            cache=cache,
        )

        views = ["mMatchupScore", "mScoreboard", "mTeam", "mRoster", "mSettings", "mMatchup"]
        league = client.get_league(views=views, use_cache=not no_cache, cache_ttl_seconds=3 * 60 * 60)
        schedule = client.get_pro_team_schedules(use_cache=not no_cache, cache_ttl_seconds=24 * 60 * 60)

        outlook_model = build_outlook(
            league_payload=league,
            schedule_payload=schedule,
            team_id=cfg.team_id,
            league_id=cfg.league_id,
        )

        typer.echo(outlook_model.model_dump_json())
    except ConfigError as exc:
        _exit(2, str(exc))
    except AuthError as exc:
        _exit(3, str(exc))
    except (ESPNError, RequestLimitError) as exc:
        _exit(4, str(exc))
    except typer.Exit:
        raise
    except Exception as exc:  # pragma: no cover
        _exit(5, f"Unexpected runtime error: {exc}")
