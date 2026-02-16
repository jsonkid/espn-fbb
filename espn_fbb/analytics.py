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
    _double_triple_counts,
    _fg_pct,
    _find_matchup_for_period,
    _ft_pct,
    _has_stats_for_period,
    _leader_sign,
    _lineup_role,
    _matchup_score,
    _matchup_score_with_ties,
    _player_stat_map,
    _roster_entries,
    _signal_lists,
    _summary_hints,
    _team_map,
    _to_float,
    _to_int,
    FGA_STAT_ID,
    FTA_STAT_ID,
    STAT_ID_MAP,
)
from espn_fbb.analytics_projection import (
    _category_stats_from_totals,
    _count_missing_season_stats,
    _infer_season_id,
    _lineup_swap_actions,
    _outlook,
    _projected_category_totals_from_starters,
    _team_projected_games,
)
from espn_fbb.analytics_schedule import _games_by_pro_team, _resolve_matchup_window, _starter_slot_counts
from espn_fbb.schema import (
    CandidateGroup,
    CandidateMeta,
    CategoryStat,
    DataQuality,
    GamesBreakdown,
    GamesRemainingBreakdown,
    LineupAction,
    Mover,
    OutlookResponse,
    PlayerCandidate,
    PreviewResponse,
    RecapResponse,
)
from espn_fbb.utils import iso_ts


def _compute_good_candidate(
    entry: dict[str, Any], scoring_period_id: int | None = None, lineup_slot_id: int = 999
) -> PlayerCandidate | None:
    player = (entry.get("playerPoolEntry") or {}).get("player") or {}
    stat_map = _player_stat_map(player, scoring_period_id=scoring_period_id)
    if not stat_map:
        return None

    pts = stat_map.get(STAT_ID_MAP["PTS"], 0.0)
    threes = stat_map.get(STAT_ID_MAP["3PM"], 0.0)
    reb = stat_map.get(STAT_ID_MAP["REB"], 0.0)
    ast = stat_map.get(STAT_ID_MAP["AST"], 0.0)
    stl = stat_map.get(STAT_ID_MAP["STL"], 0.0)
    blk = stat_map.get(STAT_ID_MAP["BLK"], 0.0)
    is_dd, is_td = _double_triple_counts(stat_map)

    reasons: list[str] = []
    impact = 0.0

    if pts >= 20:
        reasons.append("PTS>=20")
        impact += max(0.0, pts - 19) * 0.5
    if threes >= 4:
        reasons.append("3PM>=4")
        impact += max(0.0, threes - 3) * 1.0
    if reb >= 10:
        reasons.append("REB>=10")
        impact += max(0.0, reb - 9) * 0.7
    if ast >= 8:
        reasons.append("AST>=8")
        impact += max(0.0, ast - 7) * 0.9
    if stl >= 3:
        reasons.append("STL>=3")
        impact += max(0.0, stl - 2) * 1.5
    if blk >= 3:
        reasons.append("BLK>=3")
        impact += max(0.0, blk - 2) * 1.5
    if is_dd:
        reasons.append("double-double")
        impact += 2.0
    if is_td:
        reasons.append("triple-double")
        impact += 4.0

    if not reasons:
        return None

    return PlayerCandidate(
        player_id=_to_int(player.get("id", 0), 0),
        player_name=str(player.get("fullName", "Unknown")),
        lineup_slot_id=lineup_slot_id,
        lineup_role=_lineup_role(lineup_slot_id),
        impact=round(impact, 3),
        reasons=reasons,
    )


def _compute_bad_candidate(
    entry: dict[str, Any], scoring_period_id: int | None = None, lineup_slot_id: int = 999
) -> PlayerCandidate | None:
    player = (entry.get("playerPoolEntry") or {}).get("player") or {}
    stat_map = _player_stat_map(player, scoring_period_id=scoring_period_id)

    injury = str(player.get("injuryStatus", "")).upper()
    reasons: list[str] = []
    impact = 0.0

    to = stat_map.get(STAT_ID_MAP["TO"], 0.0)
    if to >= 5:
        reasons.append("TO>=5")
        impact += max(0.0, to - 4) * 1.0

    fg_pct = _fg_pct(stat_map)
    fga = stat_map.get(FGA_STAT_ID, 0.0)
    if fga >= 10 and fg_pct <= 0.40:
        reasons.append("FG%<=.40 on FGA>=10")
        impact += (0.40 - fg_pct) * 25 + (fga - 9) * 0.15

    ft_pct = _ft_pct(stat_map)
    fta = stat_map.get(FTA_STAT_ID, 0.0)
    if fta >= 6 and ft_pct <= 0.70:
        reasons.append("FT%<=.70 on FTA>=6")
        impact += (0.70 - ft_pct) * 20 + (fta - 5) * 0.15

    if injury == "OUT":
        reasons.append("OUT")
        impact += 3.0

    if not reasons:
        return None

    return PlayerCandidate(
        player_id=_to_int(player.get("id", 0), 0),
        player_name=str(player.get("fullName", "Unknown")),
        lineup_slot_id=lineup_slot_id,
        lineup_role=_lineup_role(lineup_slot_id),
        impact=round(impact, 3),
        reasons=reasons,
    )


def _candidate_lists(team: dict[str, Any], scoring_period_id: int | None = None) -> tuple[list[PlayerCandidate], list[PlayerCandidate]]:
    good: list[tuple[int, int, PlayerCandidate]] = []
    bad: list[tuple[int, int, PlayerCandidate]] = []

    for entry in _roster_entries(team):
        slot = _to_int(entry.get("lineupSlotId", 999), 999)
        player = ((entry.get("playerPoolEntry") or {}).get("player") or {})
        player_id = _to_int(player.get("id", 0), 0)

        good_c = _compute_good_candidate(entry, scoring_period_id, lineup_slot_id=slot)
        if good_c:
            good.append((slot, player_id, good_c))

        bad_c = _compute_bad_candidate(entry, scoring_period_id, lineup_slot_id=slot)
        if bad_c:
            bad.append((slot, player_id, bad_c))

    good.sort(key=lambda row: (-row[2].impact, row[0], row[1]))
    bad.sort(key=lambda row: (-row[2].impact, row[0], row[1]))
    return [x[2] for x in good], [x[2] for x in bad]


def _team_has_stats_for_period(team: dict[str, Any], scoring_period_id: int) -> bool:
    for entry in _roster_entries(team):
        player = (entry.get("playerPoolEntry") or {}).get("player") or {}
        if _has_stats_for_period(player, scoring_period_id):
            return True
    return False


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

    if has_data:
        you_good, you_bad = _candidate_lists(you_team, previous_scoring_period_id)
        opp_good, opp_bad = _candidate_lists(opp_team, previous_scoring_period_id)
        candidate_meta = CandidateMeta(
            source_scoring_period_id=previous_scoring_period_id,
            has_data=True,
            note=None,
        )
    else:
        you_good, you_bad, opp_good, opp_bad = [], [], [], []
        candidate_meta = CandidateMeta(
            source_scoring_period_id=previous_scoring_period_id,
            has_data=False,
            note="No completed games in previous scoring day; notable performances unavailable.",
        )

    return RecapResponse(
        generated_at=iso_ts(),
        league_id=league_id,
        team_id=team_id,
        matchup_period_id=matchup_period_id,
        matchup_score=_matchup_score(categories),
        categories=categories,
        movers=compute_movers(categories, yesterday_snapshot),
        candidates=CandidateGroup(
            you_good=you_good[:4],
            you_bad=you_bad[:3],
            opp_good=opp_good[:3],
            opp_bad=opp_bad[:2],
        ),
        candidates_meta=candidate_meta,
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
    opp_team = teams.get(_to_int(opp_side.get("teamId", -1), -1), {})

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
        matchup_period_id=matchup_period_id,
        projected_matchup_score=_matchup_score_with_ties(categories),
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
    opp_team = teams.get(_to_int(opp_side.get("teamId", -1), -1), {})
    starter_slot_counts = _starter_slot_counts(league_payload)

    current_scoring_period = (league_payload.get("status") or {}).get("currentScoringPeriod")
    if isinstance(current_scoring_period, list):
        current_scoring_period = current_scoring_period[0] if current_scoring_period else None
    current_scoring_period_id = _to_int(current_scoring_period, 0)
    remaining_scoring_period_ids = [pid for pid in scoring_period_ids if pid > current_scoring_period_id]

    remaining_games_map = _games_by_pro_team(
        schedule_payload, matchup_period_id, scoring_period_ids=remaining_scoring_period_ids
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
        matchup_period_id=matchup_period_id,
        current_matchup_score=_matchup_score_with_ties(current_categories),
        projected_matchup_score=_matchup_score_with_ties(projected_categories),
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
