from __future__ import annotations

from typing import Any

from espn_fbb.analytics_base import (
    MOVER_THRESHOLDS,
    _active_count,
    _category_outlook_map,
    _category_projection_map,
    _combine_category_totals,
    _compute_categories,
    _current_category_totals_from_side,
    _current_matchup_period_id,
    _fantasy_team_name,
    _find_matchup_for_period,
    _has_stats_for_period,
    _leader_sign,
    _lineup_role,
    _matchup_score,
    _matchup_score_with_ties,
    _normalize_injury_status,
    _player_stat_map,
    _roster_entries,
    _signal_lists,
    _summary_hints,
    _team_map,
    _team_standing,
    _to_float,
    _to_int,
    FGA_STAT_ID,
    FGM_STAT_ID,
    FTA_STAT_ID,
    FTM_STAT_ID,
    STAT_ID_MAP,
)
from espn_fbb.analytics_projection import (
    _category_stats_from_totals,
    _count_missing_season_stats,
    _infer_season_id,
    _lineup_swap_actions,
    _outlook,
    _projected_category_totals_from_starters,
    _season_averages_stat_map,
    _team_projected_games,
)
from espn_fbb.analytics_schedule import _games_by_pro_team, _resolve_matchup_window, _starter_slot_counts
from espn_fbb.schema import (
    CategoryStat,
    DataQuality,
    GamesBreakdown,
    GamesRemainingBreakdown,
    LineupAction,
    Mover,
    OutlookResponse,
    PeriodStats,
    PreviewResponse,
    RecapResponse,
    OutlookRosterEntry,
    OutlookRosterGroup,
    PreviewRosterEntry,
    PreviewRosterGroup,
    RecapRosterEntry,
    RecapRosterGroup,
    RosterMeta,
    SeasonAverages,
)
from espn_fbb.utils import iso_ts


def _team_has_stats_for_period(team: dict[str, Any], scoring_period_id: int) -> bool:
    for entry in _roster_entries(team):
        player = (entry.get("playerPoolEntry") or {}).get("player") or {}
        if _has_stats_for_period(player, scoring_period_id):
            return True
    return False


def _season_averages(player: dict[str, Any], season_id: int) -> SeasonAverages | None:
    stat_map = _season_averages_stat_map(player, season_id)
    if not stat_map:
        return None
    fga = stat_map.get(FGA_STAT_ID, 0.0)
    fgm = stat_map.get(FGM_STAT_ID, 0.0)
    fta = stat_map.get(FTA_STAT_ID, 0.0)
    ftm = stat_map.get(FTM_STAT_ID, 0.0)
    fg_pct = (fgm / fga) if fga > 0 else None
    ft_pct = (ftm / fta) if fta > 0 else None

    return SeasonAverages(
        pts=round(stat_map.get(STAT_ID_MAP["PTS"], 0.0), 4),
        threes=round(stat_map.get(STAT_ID_MAP["3PM"], 0.0), 4),
        reb=round(stat_map.get(STAT_ID_MAP["REB"], 0.0), 4),
        ast=round(stat_map.get(STAT_ID_MAP["AST"], 0.0), 4),
        stl=round(stat_map.get(STAT_ID_MAP["STL"], 0.0), 4),
        blk=round(stat_map.get(STAT_ID_MAP["BLK"], 0.0), 4),
        to=round(stat_map.get(STAT_ID_MAP["TO"], 0.0), 4),
        fg_pct=round(fg_pct, 4) if fg_pct is not None else None,
        ft_pct=round(ft_pct, 4) if ft_pct is not None else None,
    )


def _period_stats(stat_map: dict[int, float]) -> PeriodStats | None:
    if not stat_map:
        return None
    fga = stat_map.get(FGA_STAT_ID, 0.0)
    fgm = stat_map.get(FGM_STAT_ID, 0.0)
    fta = stat_map.get(FTA_STAT_ID, 0.0)
    ftm = stat_map.get(FTM_STAT_ID, 0.0)
    if fga > 0:
        fg_pct = fgm / fga
    else:
        fg_pct = _to_float(stat_map.get(STAT_ID_MAP["FG%"])) if STAT_ID_MAP["FG%"] in stat_map else None
    if fta > 0:
        ft_pct = ftm / fta
    else:
        ft_pct = _to_float(stat_map.get(STAT_ID_MAP["FT%"])) if STAT_ID_MAP["FT%"] in stat_map else None

    return PeriodStats(
        pts=round(stat_map.get(STAT_ID_MAP["PTS"], 0.0), 4),
        threes=round(stat_map.get(STAT_ID_MAP["3PM"], 0.0), 4),
        reb=round(stat_map.get(STAT_ID_MAP["REB"], 0.0), 4),
        ast=round(stat_map.get(STAT_ID_MAP["AST"], 0.0), 4),
        stl=round(stat_map.get(STAT_ID_MAP["STL"], 0.0), 4),
        blk=round(stat_map.get(STAT_ID_MAP["BLK"], 0.0), 4),
        to=round(stat_map.get(STAT_ID_MAP["TO"], 0.0), 4),
        fg_pct=round(fg_pct, 4) if fg_pct is not None else None,
        ft_pct=round(ft_pct, 4) if ft_pct is not None else None,
    )


def _entry_games(entry: dict[str, Any], games_by_pro_team: dict[int, int] | None) -> int | None:
    if not games_by_pro_team:
        return None
    player = (entry.get("playerPoolEntry") or {}).get("player") or {}
    pro_team_id = player.get("proTeamId")
    if pro_team_id is None:
        return 0
    return games_by_pro_team.get(_to_int(pro_team_id, -1), 0)


def _preview_roster_entries(
    team: dict[str, Any],
    season_id: int,
    *,
    games_total_by_pro_team: dict[int, int] | None = None,
) -> list[PreviewRosterEntry]:
    entries: list[PreviewRosterEntry] = []
    for entry in _roster_entries(team):
        player = (entry.get("playerPoolEntry") or {}).get("player") or {}
        status, raw = _normalize_injury_status(player.get("injuryStatus"))
        entries.append(
            PreviewRosterEntry(
                player_id=_to_int(player.get("id", 0), 0),
                player_name=str(player.get("fullName", "Unknown")),
                lineup_slot_id=_to_int(entry.get("lineupSlotId", 999), 999),
                lineup_role=_lineup_role(_to_int(entry.get("lineupSlotId", 999), 999)),
                status=status,
                status_raw=raw,
                season_avg=_season_averages(player, season_id),
                games_total=_entry_games(entry, games_total_by_pro_team),
            )
        )

    entries.sort(key=lambda e: (e.lineup_slot_id, e.player_id, e.player_name))
    return entries


def _outlook_roster_entries(
    team: dict[str, Any],
    season_id: int,
    *,
    games_played_by_pro_team: dict[int, int] | None = None,
    games_remaining_by_pro_team: dict[int, int] | None = None,
) -> list[OutlookRosterEntry]:
    entries: list[OutlookRosterEntry] = []
    for entry in _roster_entries(team):
        player = (entry.get("playerPoolEntry") or {}).get("player") or {}
        status, raw = _normalize_injury_status(player.get("injuryStatus"))
        entries.append(
            OutlookRosterEntry(
                player_id=_to_int(player.get("id", 0), 0),
                player_name=str(player.get("fullName", "Unknown")),
                lineup_slot_id=_to_int(entry.get("lineupSlotId", 999), 999),
                lineup_role=_lineup_role(_to_int(entry.get("lineupSlotId", 999), 999)),
                status=status,
                status_raw=raw,
                season_avg=_season_averages(player, season_id),
                games_played=_entry_games(entry, games_played_by_pro_team),
                games_remaining=_entry_games(entry, games_remaining_by_pro_team),
            )
        )

    entries.sort(key=lambda e: (e.lineup_slot_id, e.player_id, e.player_name))
    return entries


def _roster_entries_with_period_stats(
    team: dict[str, Any], season_id: int, scoring_period_id: int
) -> list[RecapRosterEntry]:
    entries: list[RecapRosterEntry] = []
    for entry in _roster_entries(team):
        player = (entry.get("playerPoolEntry") or {}).get("player") or {}
        stat_map = _player_stat_map(player, scoring_period_id=scoring_period_id)
        if not stat_map:
            continue
        status, raw = _normalize_injury_status(player.get("injuryStatus"))
        entries.append(
            RecapRosterEntry(
                player_id=_to_int(player.get("id", 0), 0),
                player_name=str(player.get("fullName", "Unknown")),
                lineup_slot_id=_to_int(entry.get("lineupSlotId", 999), 999),
                lineup_role=_lineup_role(_to_int(entry.get("lineupSlotId", 999), 999)),
                status=status,
                status_raw=raw,
                season_avg=_season_averages(player, season_id),
                period_stats=_period_stats(stat_map),
            )
        )

    entries.sort(key=lambda e: (e.lineup_slot_id, e.player_id, e.player_name))
    return entries


def compute_movers(categories: list[CategoryStat], yesterday_snapshot: dict[str, dict[str, float]] | None) -> list[Mover]:
    if not yesterday_snapshot:
        return []

    movers: list[Mover] = []
    for c in categories:
        y = yesterday_snapshot.get(c.key)
        if not y:
            continue

        today_margin = c.you - c.opp
        y_margin = _to_float(y.get("you")) - _to_float(y.get("opp"))
        delta = today_margin - y_margin
        threshold = MOVER_THRESHOLDS[c.key]
        if abs(delta) < threshold:
            continue

        today_sign = _leader_sign(c.key, today_margin)
        y_sign = _leader_sign(c.key, y_margin)

        if today_sign != y_sign:
            kind = "flip"
        elif abs(today_margin) < abs(y_margin):
            kind = "tighten"
        else:
            kind = "cushion"

        movers.append(
            Mover(
                key=c.key,
                kind=kind,
                delta_margin=round(delta, 4),
                today_margin=round(today_margin, 4),
                yesterday_margin=round(y_margin, 4),
            )
        )

    movers.sort(key=lambda m: abs(m.delta_margin), reverse=True)
    return movers[:5]


def build_snapshot(categories: list[CategoryStat]) -> dict[str, dict[str, float]]:
    return {c.key: {"you": c.you, "opp": c.opp} for c in categories}


def build_recap(
    league_payload: dict[str, Any],
    team_id: int,
    league_id: str,
    yesterday_snapshot: dict[str, dict[str, float]] | None = None,
) -> RecapResponse:
    matchup_period_id = _current_matchup_period_id(league_payload)
    you_side, opp_side = _find_matchup_for_period(league_payload, team_id, matchup_period_id)
    categories = _compute_categories(you_side, opp_side)

    teams = _team_map(league_payload)
    you_team = teams.get(team_id, {})
    opp_team_id = _to_int(opp_side.get("teamId", -1), -1)
    opp_team = teams.get(opp_team_id, {})

    current_scoring_period = (league_payload.get("status") or {}).get("currentScoringPeriod")
    if isinstance(current_scoring_period, list):
        current_scoring_period = current_scoring_period[0] if current_scoring_period else None
    previous_scoring_period_id = _to_int(current_scoring_period, 1) - 1
    if previous_scoring_period_id < 1:
        previous_scoring_period_id = 1

    has_your_data = _team_has_stats_for_period(you_team, previous_scoring_period_id)
    has_opp_data = _team_has_stats_for_period(opp_team, previous_scoring_period_id)
    has_data = has_your_data or has_opp_data
    season_id = _infer_season_id(league_payload, you_team)

    if has_data:
        rosters_meta = RosterMeta(
            source_scoring_period_id=previous_scoring_period_id,
            has_data=True,
            note=None,
        )
    else:
        rosters_meta = RosterMeta(
            source_scoring_period_id=previous_scoring_period_id,
            has_data=False,
            note="No completed games in previous scoring day; performance data unavailable.",
        )

    return RecapResponse(
        generated_at=iso_ts(),
        league_id=league_id,
        team_id=team_id,
        you_team_name=_fantasy_team_name(you_team),
        opp_team_id=opp_team_id if opp_team_id > 0 else None,
        opp_team_name=_fantasy_team_name(opp_team),
        matchup_period_id=matchup_period_id,
        matchup_score=_matchup_score(categories),
        categories=categories,
        movers=compute_movers(categories, yesterday_snapshot),
        rosters=RecapRosterGroup(
            you=_roster_entries_with_period_stats(you_team, season_id, previous_scoring_period_id)
            if has_your_data
            else [],
            opp=_roster_entries_with_period_stats(opp_team, season_id, previous_scoring_period_id)
            if has_opp_data
            else [],
        ),
        rosters_meta=rosters_meta,
        active_players={
            "you": _active_count(you_team),
            "opp": _active_count(opp_team),
        },
    )


def build_preview(
    league_payload: dict[str, Any],
    schedule_payload: dict[str, Any],
    team_id: int,
    league_id: str,
    week: str,
) -> PreviewResponse:
    matchup_period_id, scoring_period_ids, _ = _resolve_matchup_window(league_payload, schedule_payload, week)

    try:
        you_side, opp_side = _find_matchup_for_period(league_payload, team_id, matchup_period_id)
    except ValueError:
        you_side = {"teamId": team_id}
        opp_side = {"teamId": -1}

    teams = _team_map(league_payload)
    you_team = teams.get(team_id, {})
    opp_team_id = _to_int(opp_side.get("teamId", -1), -1)
    opp_team = teams.get(opp_team_id, {})

    games_map = _games_by_pro_team(schedule_payload, matchup_period_id, scoring_period_ids=scoring_period_ids)
    starter_slot_counts = _starter_slot_counts(league_payload)
    you_games = _team_projected_games(you_team, games_map, starter_slot_counts=starter_slot_counts)
    opp_games = _team_projected_games(opp_team, games_map, starter_slot_counts=starter_slot_counts)
    games_diff = you_games - opp_games

    season_id = _infer_season_id(league_payload, you_team)

    you_proj_totals = _projected_category_totals_from_starters(
        you_team, season_id=season_id, pro_team_games=games_map, starter_slot_counts=starter_slot_counts
    )
    opp_proj_totals = _projected_category_totals_from_starters(
        opp_team, season_id=season_id, pro_team_games=games_map, starter_slot_counts=starter_slot_counts
    )
    projected_categories = _category_stats_from_totals(you_proj_totals, opp_proj_totals)
    has_projection_signal = any(c.you != 0.0 or c.opp != 0.0 for c in projected_categories)
    categories = projected_categories if has_projection_signal else _compute_categories(you_side, opp_side)

    favored, at_risk = _signal_lists(categories)
    lineup_actions: list[LineupAction] = []
    if week == "current":
        lineup_actions = _lineup_swap_actions(
            team=you_team,
            season_id=season_id,
            pro_team_games=games_map,
            starter_slot_counts=starter_slot_counts,
            categories=categories,
            at_risk=at_risk,
        )

    return PreviewResponse(
        schema_version="2.0",
        command="matchup_preview",
        generated_at=iso_ts(),
        league_id=league_id,
        team_id=team_id,
        you_team_name=_fantasy_team_name(you_team),
        opp_team_id=opp_team_id if opp_team_id > 0 else None,
        opp_team_name=_fantasy_team_name(opp_team),
        you_standing=_team_standing(you_team),
        opp_standing=_team_standing(opp_team),
        matchup_period_id=matchup_period_id,
        projected_matchup_score=_matchup_score_with_ties(categories),
        rosters=PreviewRosterGroup(
            you=_preview_roster_entries(
                you_team,
                season_id,
                games_total_by_pro_team=games_map,
            ),
            opp=_preview_roster_entries(
                opp_team,
                season_id,
                games_total_by_pro_team=games_map,
            ),
        ),
        categories=_category_projection_map(categories),
        games=GamesBreakdown(
            you_total_games=you_games,
            opp_total_games=opp_games,
            games_diff=games_diff,
        ),
        lineup_actions=lineup_actions,
        summary_hints=_summary_hints(categories),
        data_quality=DataQuality(
            projection_basis="season_avg_x_projected_games",
            projection_used=has_projection_signal,
            season_id=season_id,
            scoring_period_ids=scoring_period_ids,
            your_starters_missing_season_stats=_count_missing_season_stats(
                you_team, season_id, games_map, starter_slot_counts
            ),
            opp_starters_missing_season_stats=_count_missing_season_stats(
                opp_team, season_id, games_map, starter_slot_counts
            ),
        ),
        outlook=_outlook(favored, at_risk, games_diff),
    )


def build_outlook(
    league_payload: dict[str, Any],
    schedule_payload: dict[str, Any],
    team_id: int,
    league_id: str,
) -> OutlookResponse:
    matchup_period_id, scoring_period_ids, _ = _resolve_matchup_window(league_payload, schedule_payload, "current")
    try:
        you_side, opp_side = _find_matchup_for_period(league_payload, team_id, matchup_period_id)
    except ValueError:
        you_side = {"teamId": team_id}
        opp_side = {"teamId": -1}

    teams = _team_map(league_payload)
    you_team = teams.get(team_id, {})
    opp_team_id = _to_int(opp_side.get("teamId", -1), -1)
    opp_team = teams.get(opp_team_id, {})
    starter_slot_counts = _starter_slot_counts(league_payload)

    current_scoring_period = (league_payload.get("status") or {}).get("currentScoringPeriod")
    if isinstance(current_scoring_period, list):
        current_scoring_period = current_scoring_period[0] if current_scoring_period else None
    current_scoring_period_id = _to_int(current_scoring_period, 0)
    remaining_scoring_period_ids = [pid for pid in scoring_period_ids if pid > current_scoring_period_id]
    played_scoring_period_ids = [pid for pid in scoring_period_ids if pid <= current_scoring_period_id]

    remaining_games_map = _games_by_pro_team(
        schedule_payload, matchup_period_id, scoring_period_ids=remaining_scoring_period_ids
    )
    played_games_map = _games_by_pro_team(
        schedule_payload, matchup_period_id, scoring_period_ids=played_scoring_period_ids
    )
    you_remaining_games = _team_projected_games(
        you_team, remaining_games_map, starter_slot_counts=starter_slot_counts
    )
    opp_remaining_games = _team_projected_games(
        opp_team, remaining_games_map, starter_slot_counts=starter_slot_counts
    )
    games_remaining_diff = you_remaining_games - opp_remaining_games

    current_categories = _compute_categories(you_side, opp_side)

    season_id = _infer_season_id(league_payload, you_team)

    you_current_totals = _current_category_totals_from_side(you_side)
    opp_current_totals = _current_category_totals_from_side(opp_side)
    you_remaining_totals = _projected_category_totals_from_starters(
        you_team,
        season_id=season_id,
        pro_team_games=remaining_games_map,
        starter_slot_counts=starter_slot_counts,
    )
    opp_remaining_totals = _projected_category_totals_from_starters(
        opp_team,
        season_id=season_id,
        pro_team_games=remaining_games_map,
        starter_slot_counts=starter_slot_counts,
    )

    you_projected_totals = _combine_category_totals(you_current_totals, you_remaining_totals)
    opp_projected_totals = _combine_category_totals(opp_current_totals, opp_remaining_totals)
    projected_categories = _category_stats_from_totals(you_projected_totals, opp_projected_totals)
    projected_favored, projected_at_risk = _signal_lists(projected_categories)
    projection_used = any(c.you != 0.0 or c.opp != 0.0 for c in projected_categories)

    return OutlookResponse(
        schema_version="2.0",
        command="matchup_outlook",
        generated_at=iso_ts(),
        league_id=league_id,
        team_id=team_id,
        you_team_name=_fantasy_team_name(you_team),
        opp_team_id=opp_team_id if opp_team_id > 0 else None,
        opp_team_name=_fantasy_team_name(opp_team),
        you_standing=_team_standing(you_team),
        opp_standing=_team_standing(opp_team),
        matchup_period_id=matchup_period_id,
        current_matchup_score=_matchup_score_with_ties(current_categories),
        projected_matchup_score=_matchup_score_with_ties(projected_categories),
        rosters=OutlookRosterGroup(
            you=_outlook_roster_entries(
                you_team,
                season_id,
                games_played_by_pro_team=played_games_map,
                games_remaining_by_pro_team=remaining_games_map,
            ),
            opp=_outlook_roster_entries(
                opp_team,
                season_id,
                games_played_by_pro_team=played_games_map,
                games_remaining_by_pro_team=remaining_games_map,
            ),
        ),
        categories=_category_outlook_map(current_categories, projected_categories),
        games_remaining=GamesRemainingBreakdown(
            you_remaining_games=you_remaining_games,
            opp_remaining_games=opp_remaining_games,
            games_remaining_diff=games_remaining_diff,
        ),
        summary_hints=_summary_hints(projected_categories, current_categories=current_categories),
        data_quality=DataQuality(
            projection_basis="current_totals_plus_remaining_season_avg_x_projected_games",
            projection_used=projection_used,
            season_id=season_id,
            scoring_period_ids=remaining_scoring_period_ids,
            your_starters_missing_season_stats=_count_missing_season_stats(
                you_team, season_id, remaining_games_map, starter_slot_counts
            ),
            opp_starters_missing_season_stats=_count_missing_season_stats(
                opp_team, season_id, remaining_games_map, starter_slot_counts
            ),
        ),
        outlook=_outlook(projected_favored, projected_at_risk, games_remaining_diff),
    )
