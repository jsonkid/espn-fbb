from __future__ import annotations

from typing import Any

from espn_fbb.schema import (
    CategoryOutlook,
    CategoryProjection,
    CategorySignal,
    CategoryStat,
    SummaryHints,
)

CATEGORY_ORDER = ["FG%", "FT%", "3PM", "REB", "AST", "STL", "BLK", "TO", "PTS"]
STAT_ID_MAP = {
    "PTS": 0,
    "BLK": 1,
    "STL": 2,
    "AST": 3,
    "REB": 6,
    "TO": 11,
    "3PM": 17,
    "FG%": 19,
    "FT%": 20,
}

FGA_STAT_ID = 14
FGM_STAT_ID = 13
FTA_STAT_ID = 16
FTM_STAT_ID = 15

MOVER_THRESHOLDS = {
    "3PM": 4,
    "REB": 12,
    "AST": 10,
    "STL": 4,
    "BLK": 4,
    "PTS": 40,
    "TO": 6,
    "FG%": 0.010,
    "FT%": 0.010,
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _status_for_category(cat: str, you: float, opp: float) -> str:
    if cat == "TO":
        if you < opp:
            return "you"
        if you > opp:
            return "opp"
        return "tie"
    if you > opp:
        return "you"
    if you < opp:
        return "opp"
    return "tie"


def _pdiff(cat: str, you: float, opp: float) -> float:
    if opp == 0:
        if you == 0:
            return 0.0
        if cat == "TO":
            return 1.0 if you < opp else -1.0
        return 1.0 if you > opp else -1.0
    if cat == "TO":
        return (opp - you) / abs(opp)
    return (you - opp) / abs(opp)


def _extract_raw_score_by_stat(side: dict[str, Any]) -> dict[int, float]:
    score_root = side.get("cumulativeScore") or side.get("totalPoints") or {}
    raw = score_root.get("scoreByStat") or score_root.get("pointsByStat") or side.get("pointsByStat") or {}
    by_stat: dict[int, float] = {}
    if isinstance(raw, dict):
        for stat_id, val in raw.items():
            if isinstance(val, dict):
                score = val.get("score", val.get("value", 0))
            else:
                score = val
            try:
                by_stat[int(stat_id)] = _to_float(score)
            except (TypeError, ValueError):
                continue
    elif isinstance(raw, list):
        for row in raw:
            stat_id = row.get("statId")
            score = row.get("score", row.get("value", 0))
            if stat_id is None:
                continue
            by_stat[int(stat_id)] = _to_float(score)
    return by_stat


def _extract_points_by_stat(side: dict[str, Any]) -> dict[str, float]:
    by_stat = _extract_raw_score_by_stat(side)
    return {cat: by_stat.get(stat_id, 0.0) for cat, stat_id in STAT_ID_MAP.items()}


def _find_matchup_for_period(league: dict[str, Any], team_id: int, matchup_period_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    for matchup in league.get("schedule", []):
        if _to_int(matchup.get("matchupPeriodId", -1), -1) != matchup_period_id:
            continue
        home = matchup.get("home", {})
        away = matchup.get("away", {})
        home_id = _to_int(home.get("teamId", -1), -1)
        away_id = _to_int(away.get("teamId", -1), -1)
        if home_id == team_id:
            return home, away
        if away_id == team_id:
            return away, home
    raise ValueError(f"No matchup found for team_id={team_id} matchup_period_id={matchup_period_id}")


def _current_matchup_period_id(league: dict[str, Any]) -> int:
    status = league.get("status", {})
    current = status.get("currentMatchupPeriod")
    if current is not None:
        if isinstance(current, list):
            current = current[0] if current else None
        return _to_int(current, 1)
    schedule = league.get("schedule", [])
    if not schedule:
        raise ValueError("League payload has no schedule")
    return _to_int(schedule[0].get("matchupPeriodId", 1), 1)


def _team_map(league: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for team in league.get("teams", []):
        team_id = team.get("id")
        if team_id is None:
            continue
        out[_to_int(team_id, -1)] = team
    return out


def _player_stat_map(player: dict[str, Any], scoring_period_id: int | None = None) -> dict[int, float]:
    stats = player.get("stats", [])
    preferred: dict[str, Any] | None = None

    for row in stats:
        stat_source_id = row.get("statSourceId")
        if stat_source_id is not None and _to_int(stat_source_id, -1) != 0:
            continue
        if scoring_period_id is not None:
            row_period = row.get("scoringPeriodId")
            if isinstance(row_period, list):
                row_period = row_period[0] if row_period else None
            if row_period is not None and _to_int(row_period, -1) == scoring_period_id:
                preferred = row
                break
            continue
        if preferred is None and row.get("stats"):
            preferred = row

    if preferred is None:
        return {}

    raw = preferred.get("stats", {})
    out: dict[int, float] = {}
    for k, v in raw.items():
        try:
            out[int(k)] = _to_float(v)
        except (TypeError, ValueError):
            continue
    return out


def _has_stats_for_period(player: dict[str, Any], scoring_period_id: int) -> bool:
    stats = player.get("stats", [])
    for row in stats:
        stat_source_id = row.get("statSourceId")
        if stat_source_id is not None and _to_int(stat_source_id, -1) != 0:
            continue
        row_period = row.get("scoringPeriodId")
        if isinstance(row_period, list):
            row_period = row_period[0] if row_period else None
        if row_period is None or _to_int(row_period, -1) != scoring_period_id:
            continue
        row_stats = row.get("stats", {})
        return bool(row_stats)
    return False


def _fg_pct(stat_map: dict[int, float]) -> float:
    if STAT_ID_MAP["FG%"] in stat_map:
        return stat_map[STAT_ID_MAP["FG%"]]
    fga = stat_map.get(FGA_STAT_ID, 0.0)
    if fga <= 0:
        return 0.0
    return stat_map.get(FGM_STAT_ID, 0.0) / fga


def _ft_pct(stat_map: dict[int, float]) -> float:
    if STAT_ID_MAP["FT%"] in stat_map:
        return stat_map[STAT_ID_MAP["FT%"]]
    fta = stat_map.get(FTA_STAT_ID, 0.0)
    if fta <= 0:
        return 0.0
    return stat_map.get(FTM_STAT_ID, 0.0) / fta


def _double_triple_counts(stat_map: dict[int, float]) -> tuple[bool, bool]:
    major = [
        stat_map.get(STAT_ID_MAP["PTS"], 0.0),
        stat_map.get(STAT_ID_MAP["REB"], 0.0),
        stat_map.get(STAT_ID_MAP["AST"], 0.0),
        stat_map.get(STAT_ID_MAP["STL"], 0.0),
        stat_map.get(STAT_ID_MAP["BLK"], 0.0),
    ]
    count = sum(1 for x in major if x >= 10)
    return count >= 2, count >= 3


def _lineup_role(lineup_slot_id: int) -> str:
    return "starter" if lineup_slot_id >= 0 and lineup_slot_id not in {12, 13, 14, 15, 16, 17} else "bench"


def _roster_entries(team: dict[str, Any]) -> list[dict[str, Any]]:
    roster = team.get("roster", {})
    entries = roster.get("entries")
    if isinstance(entries, list):
        return entries
    return []


def _active_count(team: dict[str, Any]) -> int:
    count = 0
    for entry in _roster_entries(team):
        slot = _to_int(entry.get("lineupSlotId", -1), -1)
        if 0 <= slot <= 12:
            count += 1
    return count


def _compute_categories(you_side: dict[str, Any], opp_side: dict[str, Any]) -> list[CategoryStat]:
    you_scores = _extract_points_by_stat(you_side)
    opp_scores = _extract_points_by_stat(opp_side)

    out: list[CategoryStat] = []
    for cat in CATEGORY_ORDER:
        you = _to_float(you_scores.get(cat))
        opp = _to_float(opp_scores.get(cat))
        out.append(
            CategoryStat(
                key=cat,
                you=round(you, 4),
                opp=round(opp, 4),
                margin=round(you - opp, 4),
                status=_status_for_category(cat, you, opp),
            )
        )
    return out


def _matchup_score(categories: list[CategoryStat]) -> dict[str, int]:
    you = sum(1 for c in categories if c.status == "you")
    opp = sum(1 for c in categories if c.status == "opp")
    return {"you": you, "opp": opp}


def _matchup_score_with_ties(categories: list[CategoryStat]) -> dict[str, int]:
    you = sum(1 for c in categories if c.status == "you")
    opp = sum(1 for c in categories if c.status == "opp")
    tie = sum(1 for c in categories if c.status == "tie")
    return {"you": you, "opp": opp, "tie": tie}


def _signal_lists(categories: list[CategoryStat]) -> tuple[list[CategorySignal], list[CategorySignal]]:
    favored: list[CategorySignal] = []
    at_risk: list[CategorySignal] = []

    for c in categories:
        pd = _pdiff(c.key, c.you, c.opp)
        if pd >= 0.10:
            favored.append(CategorySignal(key=c.key, pdiff=round(pd, 4)))
        elif pd <= -0.10:
            at_risk.append(CategorySignal(key=c.key, pdiff=round(pd, 4)))

    favored = sorted(favored, key=lambda x: x.pdiff, reverse=True)[:4]
    at_risk = sorted(at_risk, key=lambda x: x.pdiff)[:4]
    return favored, at_risk


def _signal_label(pdiff: float) -> str:
    if pdiff >= 0.10:
        return "favored"
    if pdiff <= -0.10:
        return "at_risk"
    return "neutral"


def _category_projection_map(categories: list[CategoryStat]) -> dict[str, CategoryProjection]:
    out: dict[str, CategoryProjection] = {}
    for c in categories:
        pd = round(_pdiff(c.key, c.you, c.opp), 4)
        out[c.key] = CategoryProjection(
            projected_you=round(c.you, 4),
            projected_opp=round(c.opp, 4),
            projected_margin=round(c.margin, 4),
            projected_status=c.status,
            projected_pdiff=pd,
            projected_signal=_signal_label(pd),
        )
    return out


def _category_outlook_map(
    current_categories: list[CategoryStat], projected_categories: list[CategoryStat]
) -> dict[str, CategoryOutlook]:
    current_map = {c.key: c for c in current_categories}
    projected_map = {c.key: c for c in projected_categories}
    out: dict[str, CategoryOutlook] = {}
    for key in CATEGORY_ORDER:
        cc = current_map[key]
        pc = projected_map[key]
        cp = round(_pdiff(key, cc.you, cc.opp), 4)
        pp = round(_pdiff(key, pc.you, pc.opp), 4)
        out[key] = CategoryOutlook(
            current_you=round(cc.you, 4),
            current_opp=round(cc.opp, 4),
            current_margin=round(cc.margin, 4),
            current_status=cc.status,
            current_pdiff=cp,
            current_signal=_signal_label(cp),
            projected_you=round(pc.you, 4),
            projected_opp=round(pc.opp, 4),
            projected_margin=round(pc.margin, 4),
            projected_status=pc.status,
            projected_pdiff=pp,
            projected_signal=_signal_label(pp),
        )
    return out


def _summary_hints(
    projected_categories: list[CategoryStat], current_categories: list[CategoryStat] | None = None
) -> SummaryHints:
    sorted_by_abs = sorted(projected_categories, key=lambda c: abs(c.margin))
    biggest_adv = sorted([c for c in projected_categories if c.status == "you"], key=lambda c: c.margin, reverse=True)
    biggest_dis = sorted([c for c in projected_categories if c.status == "opp"], key=lambda c: c.margin)
    swings: list[str] = []
    if current_categories is not None:
        current_status = {c.key: c.status for c in current_categories}
        for c in projected_categories:
            if current_status.get(c.key) != c.status:
                swings.append(c.key)
    return SummaryHints(
        closest_categories=[c.key for c in sorted_by_abs[:3]],
        biggest_advantages=[c.key for c in biggest_adv[:3]],
        biggest_disadvantages=[c.key for c in biggest_dis[:3]],
        swing_categories=swings,
    )


def _leader_sign(category: str, margin: float) -> int:
    if abs(margin) < 1e-12:
        return 0
    if category == "TO":
        return -1 if margin > 0 else 1
    return 1 if margin > 0 else -1


def _current_category_totals_from_side(side: dict[str, Any]) -> dict[str, float]:
    by_stat = _extract_raw_score_by_stat(side)
    fgm = by_stat.get(FGM_STAT_ID, 0.0)
    fga = by_stat.get(FGA_STAT_ID, 0.0)
    ftm = by_stat.get(FTM_STAT_ID, 0.0)
    fta = by_stat.get(FTA_STAT_ID, 0.0)
    totals = {
        "3PM": by_stat.get(STAT_ID_MAP["3PM"], 0.0),
        "REB": by_stat.get(STAT_ID_MAP["REB"], 0.0),
        "AST": by_stat.get(STAT_ID_MAP["AST"], 0.0),
        "STL": by_stat.get(STAT_ID_MAP["STL"], 0.0),
        "BLK": by_stat.get(STAT_ID_MAP["BLK"], 0.0),
        "TO": by_stat.get(STAT_ID_MAP["TO"], 0.0),
        "PTS": by_stat.get(STAT_ID_MAP["PTS"], 0.0),
        "FGM": fgm,
        "FGA": fga,
        "FTM": ftm,
        "FTA": fta,
    }
    totals["FG%"] = (fgm / fga) if fga > 0 else _to_float(by_stat.get(STAT_ID_MAP["FG%"], 0.0))
    totals["FT%"] = (ftm / fta) if fta > 0 else _to_float(by_stat.get(STAT_ID_MAP["FT%"], 0.0))
    return totals


def _combine_category_totals(current: dict[str, float], remaining: dict[str, float]) -> dict[str, float]:
    totals = {cat: _to_float(current.get(cat)) + _to_float(remaining.get(cat)) for cat in CATEGORY_ORDER}
    fgm = _to_float(current.get("FGM")) + _to_float(remaining.get("FGM"))
    fga = _to_float(current.get("FGA")) + _to_float(remaining.get("FGA"))
    ftm = _to_float(current.get("FTM")) + _to_float(remaining.get("FTM"))
    fta = _to_float(current.get("FTA")) + _to_float(remaining.get("FTA"))
    totals["FGM"] = fgm
    totals["FGA"] = fga
    totals["FTM"] = ftm
    totals["FTA"] = fta
    totals["FG%"] = (fgm / fga) if fga > 0 else 0.0
    totals["FT%"] = (ftm / fta) if fta > 0 else 0.0
    return totals
