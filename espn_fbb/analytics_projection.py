from __future__ import annotations

from typing import Any

from espn_fbb.analytics_base import (
    CATEGORY_ORDER,
    FGA_STAT_ID,
    FGM_STAT_ID,
    FTA_STAT_ID,
    FTM_STAT_ID,
    STAT_ID_MAP,
    _roster_entries,
    _status_for_category,
    _to_float,
    _to_int,
)
from espn_fbb.schema import CategorySignal, CategoryStat, LineupAction


def _entry_projected_games(entry: dict[str, Any], pro_team_games: dict[int, int]) -> int:
    player = (entry.get("playerPoolEntry") or {}).get("player") or {}
    pro_team_id = player.get("proTeamId")
    if pro_team_id is None:
        return 0
    return pro_team_games.get(_to_int(pro_team_id, -1), 0)


def _projected_starter_entries(
    team: dict[str, Any], pro_team_games: dict[int, int], starter_slot_counts: dict[int, int]
) -> list[dict[str, Any]]:
    starter_slots = set(starter_slot_counts.keys())
    starter_target = sum(starter_slot_counts.values())
    ir_slots = {13, 14, 15, 16, 17}

    entries = _roster_entries(team)
    locked_starters: list[dict[str, Any]] = []
    bench_candidates: list[dict[str, Any]] = []

    for entry in entries:
        slot = _to_int(entry.get("lineupSlotId", -1), -1)
        player = (entry.get("playerPoolEntry") or {}).get("player") or {}
        injury = str(player.get("injuryStatus", "")).upper()
        if slot in starter_slots:
            if injury != "OUT":
                locked_starters.append(entry)
        elif slot not in ir_slots and injury != "OUT":
            bench_candidates.append(entry)

    selected = list(locked_starters)
    selected_ids = {_to_int(((e.get("playerPoolEntry") or {}).get("player") or {}).get("id"), -1) for e in selected}
    bench_candidates.sort(key=lambda e: _entry_projected_games(e, pro_team_games), reverse=True)

    for entry in bench_candidates:
        if len(selected) >= starter_target:
            break
        pid = _to_int(((entry.get("playerPoolEntry") or {}).get("player") or {}).get("id"), -1)
        if pid in selected_ids:
            continue
        selected.append(entry)
        selected_ids.add(pid)

    if len(selected) < starter_target:
        for entry in entries:
            slot = _to_int(entry.get("lineupSlotId", -1), -1)
            if slot not in starter_slots:
                continue
            pid = _to_int(((entry.get("playerPoolEntry") or {}).get("player") or {}).get("id"), -1)
            if pid in selected_ids:
                continue
            selected.append(entry)
            selected_ids.add(pid)
            if len(selected) >= starter_target:
                break

    return selected


def _team_projected_games(
    team: dict[str, Any], pro_team_games: dict[int, int], starter_slot_counts: dict[int, int]
) -> int:
    selected = _projected_starter_entries(team, pro_team_games, starter_slot_counts)
    return sum(_entry_projected_games(entry, pro_team_games) for entry in selected)


def _season_totals_stat_map(player: dict[str, Any], season_id: int) -> dict[int, float]:
    for row in player.get("stats", []):
        if _to_int(row.get("statSourceId"), -1) != 0:
            continue
        if _to_int(row.get("statSplitTypeId"), -1) != 0:
            continue
        if _to_int(row.get("seasonId"), -1) != season_id:
            continue
        if _to_int(row.get("scoringPeriodId"), -1) != 0:
            continue
        raw = row.get("stats", {})
        out: dict[int, float] = {}
        for k, v in raw.items():
            out[_to_int(k, -1)] = _to_float(v)
        return out
    return {}


def _season_averages_stat_map(player: dict[str, Any], season_id: int) -> dict[int, float]:
    stat_map = _season_totals_stat_map(player, season_id)
    gp = stat_map.get(42, 0.0)
    if gp <= 0:
        return {}
    return {stat_id: value / gp for stat_id, value in stat_map.items()}


def _projected_category_totals_from_starters(
    team: dict[str, Any],
    season_id: int,
    pro_team_games: dict[int, int],
    starter_slot_counts: dict[int, int],
) -> dict[str, float]:
    selected = _projected_starter_entries(team, pro_team_games, starter_slot_counts)
    totals = {cat: 0.0 for cat in CATEGORY_ORDER}
    fgm = 0.0
    fga = 0.0
    ftm = 0.0
    fta = 0.0

    for entry in selected:
        player = (entry.get("playerPoolEntry") or {}).get("player") or {}
        stat_map = _season_totals_stat_map(player, season_id)
        if not stat_map:
            continue
        gp = stat_map.get(42, 0.0)
        if gp <= 0:
            continue
        games = float(_entry_projected_games(entry, pro_team_games))
        if games <= 0:
            continue

        def per_game(stat_id: int) -> float:
            return stat_map.get(stat_id, 0.0) / gp

        totals["3PM"] += per_game(STAT_ID_MAP["3PM"]) * games
        totals["REB"] += per_game(STAT_ID_MAP["REB"]) * games
        totals["AST"] += per_game(STAT_ID_MAP["AST"]) * games
        totals["STL"] += per_game(STAT_ID_MAP["STL"]) * games
        totals["BLK"] += per_game(STAT_ID_MAP["BLK"]) * games
        totals["TO"] += per_game(STAT_ID_MAP["TO"]) * games
        totals["PTS"] += per_game(STAT_ID_MAP["PTS"]) * games
        fgm += per_game(FGM_STAT_ID) * games
        fga += per_game(FGA_STAT_ID) * games
        ftm += per_game(FTM_STAT_ID) * games
        fta += per_game(FTA_STAT_ID) * games

    totals["FG%"] = (fgm / fga) if fga > 0 else 0.0
    totals["FT%"] = (ftm / fta) if fta > 0 else 0.0
    totals["FGM"] = fgm
    totals["FGA"] = fga
    totals["FTM"] = ftm
    totals["FTA"] = fta
    return totals


def _category_stats_from_totals(you_totals: dict[str, float], opp_totals: dict[str, float]) -> list[CategoryStat]:
    out: list[CategoryStat] = []
    for cat in CATEGORY_ORDER:
        you = _to_float(you_totals.get(cat))
        opp = _to_float(opp_totals.get(cat))
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


def _entry_name(entry: dict[str, Any]) -> str:
    player = (entry.get("playerPoolEntry") or {}).get("player") or {}
    return str(player.get("fullName", "Unknown"))


def _entry_player_id(entry: dict[str, Any]) -> int:
    player = (entry.get("playerPoolEntry") or {}).get("player") or {}
    return _to_int(player.get("id"), 0)


def _entry_injury(entry: dict[str, Any]) -> str:
    player = (entry.get("playerPoolEntry") or {}).get("player") or {}
    return str(player.get("injuryStatus", "")).upper()


def _entry_projected_contrib(
    entry: dict[str, Any], season_id: int, pro_team_games: dict[int, int], *, treat_out_as_zero: bool
) -> dict[str, float]:
    if treat_out_as_zero and _entry_injury(entry) == "OUT":
        return {"PTS": 0.0, "3PM": 0.0, "REB": 0.0, "AST": 0.0, "STL": 0.0, "BLK": 0.0, "TO": 0.0}

    player = (entry.get("playerPoolEntry") or {}).get("player") or {}
    stat_map = _season_totals_stat_map(player, season_id)
    gp = stat_map.get(42, 0.0)
    games = float(_entry_projected_games(entry, pro_team_games))
    if not stat_map or gp <= 0 or games <= 0:
        return {"PTS": 0.0, "3PM": 0.0, "REB": 0.0, "AST": 0.0, "STL": 0.0, "BLK": 0.0, "TO": 0.0}

    def per_game(stat_id: int) -> float:
        return stat_map.get(stat_id, 0.0) / gp

    return {
        "PTS": per_game(STAT_ID_MAP["PTS"]) * games,
        "3PM": per_game(STAT_ID_MAP["3PM"]) * games,
        "REB": per_game(STAT_ID_MAP["REB"]) * games,
        "AST": per_game(STAT_ID_MAP["AST"]) * games,
        "STL": per_game(STAT_ID_MAP["STL"]) * games,
        "BLK": per_game(STAT_ID_MAP["BLK"]) * games,
        "TO": per_game(STAT_ID_MAP["TO"]) * games,
    }


def _lineup_swap_actions(
    team: dict[str, Any],
    season_id: int,
    pro_team_games: dict[int, int],
    starter_slot_counts: dict[int, int],
    categories: list[CategoryStat],
    at_risk: list[CategorySignal],
) -> list[LineupAction]:
    starter_slots = set(starter_slot_counts.keys())
    ir_slots = {13, 14, 15, 16, 17}
    entries = _roster_entries(team)

    starters = [e for e in entries if _to_int(e.get("lineupSlotId", -1), -1) in starter_slots]
    bench = [
        e
        for e in entries
        if _to_int(e.get("lineupSlotId", -1), -1) not in starter_slots
        and _to_int(e.get("lineupSlotId", -1), -1) not in ir_slots
        and _entry_injury(e) != "OUT"
    ]

    at_risk_keys = {x.key for x in at_risk}
    to_margin = next((c.margin for c in categories if c.key == "TO"), 0.0)
    suggestions: list[tuple[int, float, LineupAction]] = []
    relaxed: list[tuple[int, float, LineupAction]] = []

    for st in starters:
        st_games = float(_entry_projected_games(st, pro_team_games))
        if _entry_injury(st) == "OUT":
            st_games = 0.0
        st_contrib = _entry_projected_contrib(st, season_id, pro_team_games, treat_out_as_zero=True)

        for bn in bench:
            if _to_int(((bn.get("playerPoolEntry") or {}).get("player") or {}).get("id"), -1) == _to_int(
                ((st.get("playerPoolEntry") or {}).get("player") or {}).get("id"), -1
            ):
                continue

            bn_games = float(_entry_projected_games(bn, pro_team_games))
            games_delta = bn_games - st_games
            if games_delta < 2.0:
                continue

            bn_contrib = _entry_projected_contrib(bn, season_id, pro_team_games, treat_out_as_zero=False)
            delta = {k: bn_contrib[k] - st_contrib[k] for k in st_contrib.keys()}

            improved_at_risk = 0
            improved = 0
            worsened = 0
            for cat in ("PTS", "3PM", "REB", "AST", "STL", "BLK", "TO"):
                improvement = -delta[cat] if cat == "TO" else delta[cat]
                if improvement > 0:
                    improved += 1
                    if cat in at_risk_keys:
                        improved_at_risk += 1
                elif improvement < 0:
                    worsened += 1

            net_score = improved - worsened

            action = LineupAction(
                type="swap",
                out_player_id=_entry_player_id(st),
                out_player_name=_entry_name(st),
                in_player_id=_entry_player_id(bn),
                in_player_name=_entry_name(bn),
                games_delta=round(games_delta, 1),
                category_deltas={k: round(v, 2) for k, v in delta.items()},
                score=net_score,
            )

            if delta["TO"] > 1.5 and ("TO" in at_risk_keys or abs(to_margin) < 2.0):
                continue
            if net_score >= 1:
                relaxed.append((net_score, games_delta, action))
            if improved_at_risk < 2 or worsened > 1 or net_score < 2:
                continue
            suggestions.append((net_score, games_delta, action))

    if not suggestions and relaxed:
        suggestions = relaxed

    suggestions.sort(
        key=lambda x: (
            -x[0],
            -x[1],
            x[2].in_player_id,
            x[2].out_player_id,
            x[2].in_player_name,
            x[2].out_player_name,
        )
    )
    deduped: list[LineupAction] = []
    seen_in: set[int] = set()
    for _, _, action in suggestions:
        if action.in_player_id in seen_in:
            continue
        seen_in.add(action.in_player_id)
        deduped.append(action)
        if len(deduped) >= 3:
            break
    return deduped


def _outlook(favored: list[CategorySignal], at_risk: list[CategorySignal], games_diff: int) -> dict[str, str]:
    cat_edge = len(favored) - len(at_risk)
    if cat_edge >= 3 and games_diff >= 3:
        label = "Strong Lean You"
    elif cat_edge >= 1:
        label = "Lean You"
    elif cat_edge == 0:
        label = "Toss-up"
    elif cat_edge <= -3 and games_diff <= -3:
        label = "Strong Lean Opponent"
    else:
        label = "Lean Opponent"

    reason = f"Favored in {len(favored)} cats; {games_diff:+d} games"
    return {"label": label, "reason": reason}


def _infer_season_id(league_payload: dict[str, Any], you_team: dict[str, Any]) -> int:
    season_id = _to_int((league_payload.get("status") or {}).get("seasonId"), 0)
    if season_id <= 0:
        season_id = _to_int((league_payload.get("seasonId")), 0)
    if season_id > 0:
        return season_id
    max_season = 0
    for entry in _roster_entries(you_team):
        player = (entry.get("playerPoolEntry") or {}).get("player") or {}
        for row in player.get("stats", []):
            max_season = max(max_season, _to_int(row.get("seasonId"), 0))
    return max_season


def _count_missing_season_stats(
    team: dict[str, Any], season_id: int, pro_team_games: dict[int, int], starter_slot_counts: dict[int, int]
) -> int:
    missing = 0
    for entry in _projected_starter_entries(team, pro_team_games, starter_slot_counts):
        player = (entry.get("playerPoolEntry") or {}).get("player") or {}
        if not _season_totals_stat_map(player, season_id):
            missing += 1
    return missing
