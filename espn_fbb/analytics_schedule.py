from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from espn_fbb.analytics_base import _current_matchup_period_id, _to_int


def _matchup_scoring_period_ids(league_payload: dict[str, Any], matchup_period_id: int) -> list[int]:
    settings = league_payload.get("settings", {})
    schedule_settings = settings.get("scheduleSettings", {})
    matchup_periods = schedule_settings.get("matchupPeriods", {})

    def _normalize_period_list(value: Any) -> list[int]:
        if isinstance(value, list):
            return [x for x in (_to_int(v, -1) for v in value) if x > 0]
        return []

    def _extract_bounds(row: dict[str, Any]) -> tuple[int | None, int | None]:
        start = None
        end = None
        for key in ("startScoringPeriodId", "firstScoringPeriod", "start"):
            if key in row:
                start = _to_int(row.get(key), -1)
                if start > 0:
                    break
        for key in ("endScoringPeriodId", "lastScoringPeriod", "end"):
            if key in row:
                end = _to_int(row.get(key), -1)
                if end > 0:
                    break
        if start is not None and end is not None and start > 0 and end > 0 and end >= start:
            return start, end
        return None, None

    if isinstance(matchup_periods, dict):
        inverted_ids: list[int] = []
        for maybe_scoring_id, maybe_matchup_ids in matchup_periods.items():
            if not isinstance(maybe_matchup_ids, list):
                continue
            matchup_ids = [_to_int(v, -1) for v in maybe_matchup_ids]
            if matchup_period_id in matchup_ids:
                sp_id = _to_int(maybe_scoring_id, -1)
                if sp_id > 0:
                    inverted_ids.append(sp_id)
        if inverted_ids:
            return sorted(set(inverted_ids))

        row = matchup_periods.get(str(matchup_period_id), matchup_periods.get(matchup_period_id))
        if isinstance(row, list):
            ids = _normalize_period_list(row)
            if ids:
                return ids
        if isinstance(row, dict):
            for key in ("scoringPeriods", "scoringPeriodIds"):
                ids = _normalize_period_list(row.get(key))
                if ids:
                    return ids
            start, end = _extract_bounds(row)
            if start is not None and end is not None:
                return list(range(start, end + 1))
    elif isinstance(matchup_periods, list):
        for row in matchup_periods:
            if not isinstance(row, dict):
                continue
            row_id = _to_int(row.get("id", row.get("matchupPeriodId", -1)), -1)
            if row_id != matchup_period_id:
                continue
            for key in ("scoringPeriods", "scoringPeriodIds"):
                ids = _normalize_period_list(row.get(key))
                if ids:
                    return ids
            start, end = _extract_bounds(row)
            if start is not None and end is not None:
                return list(range(start, end + 1))

    return []


def _games_by_pro_team(
    schedule_payload: dict[str, Any], matchup_period_id: int, scoring_period_ids: list[int] | None = None
) -> dict[int, int]:
    sources = schedule_payload.get("proTeams")
    if not isinstance(sources, list):
        sources = (schedule_payload.get("settings") or {}).get("proTeams", [])

    def _games_from_value(value: Any, period_id: int) -> int:
        if value is None:
            return 0
        if isinstance(value, (int, float, str)):
            return _to_int(value, 0)
        if isinstance(value, list):
            if not value:
                return 0
            if all(isinstance(item, dict) for item in value):
                count = 0
                for item in value:
                    item_period = item.get("matchupPeriodId", item.get("scoringPeriodId"))
                    if item_period is None or _to_int(item_period, period_id) == period_id:
                        count += 1
                return count
            return len(value)
        if isinstance(value, dict):
            if "value" in value:
                return _games_from_value(value.get("value"), period_id)
            if "gameCount" in value:
                return _to_int(value.get("gameCount"), 0)
            return sum(_games_from_value(nested, period_id) for nested in value.values())
        return 0

    out: dict[int, int] = {}
    for row in sources:
        pro_id = row.get("id")
        if pro_id is None:
            continue

        games = 0
        matchup_map = row.get("proGamesByMatchupPeriod", {})
        if isinstance(matchup_map, dict):
            if str(matchup_period_id) in matchup_map:
                games = _games_from_value(matchup_map[str(matchup_period_id)], matchup_period_id)
            elif matchup_period_id in matchup_map:
                games = _games_from_value(matchup_map[matchup_period_id], matchup_period_id)

        if not games:
            scoring_map = row.get("proGamesByScoringPeriod", {})
            if isinstance(scoring_map, dict):
                period_ids = scoring_period_ids or []
                if period_ids:
                    games = sum(
                        _games_from_value(
                            scoring_map.get(str(period_id), scoring_map.get(period_id)),
                            period_id,
                        )
                        for period_id in period_ids
                    )
                elif str(matchup_period_id) in scoring_map or matchup_period_id in scoring_map:
                    games = _games_from_value(
                        scoring_map.get(str(matchup_period_id), scoring_map.get(matchup_period_id)),
                        matchup_period_id,
                    )
                else:
                    games = sum(_games_from_value(v, matchup_period_id) for v in scoring_map.values())
            elif isinstance(scoring_map, list):
                period_ids = scoring_period_ids or []
                if period_ids and all(isinstance(item, (int, float, str, type(None))) for item in scoring_map):
                    for period_id in period_ids:
                        if 0 <= period_id < len(scoring_map):
                            games += _to_int(scoring_map[period_id], 0)
                else:
                    games = _games_from_value(scoring_map, matchup_period_id)
        if not games:
            sched = row.get("schedule", [])
            if isinstance(sched, list):
                games = sum(1 for g in sched if _to_int(g.get("matchupPeriodId", -1), -1) == matchup_period_id)

        out[_to_int(pro_id, -1)] = games
    return out


def _starter_slot_counts(league_payload: dict[str, Any]) -> dict[int, int]:
    lineup_slot_counts = ((league_payload.get("settings") or {}).get("rosterSettings") or {}).get("lineupSlotCounts", {})
    if not isinstance(lineup_slot_counts, dict) or not lineup_slot_counts:
        return {slot: 1 for slot in range(0, 12) if slot not in {12, 13, 14, 15, 16, 17}}

    bench_ir_slots = {12, 13, 14, 15, 16, 17}
    out: dict[int, int] = {}
    for slot_id, count in lineup_slot_counts.items():
        slot = _to_int(slot_id, -1)
        cnt = _to_int(count, 0)
        if slot < 0 or cnt <= 0 or slot in bench_ir_slots:
            continue
        out[slot] = cnt
    return out


def _scoring_period_dates(schedule_payload: dict[str, Any]) -> dict[int, date]:
    pro_rows = schedule_payload.get("proTeams")
    if not isinstance(pro_rows, list):
        pro_rows = (schedule_payload.get("settings") or {}).get("proTeams", [])
    if not isinstance(pro_rows, list):
        return {}

    et = ZoneInfo("America/New_York")
    out: dict[int, date] = {}
    for row in pro_rows:
        mapping = row.get("proGamesByScoringPeriod", {})
        if not isinstance(mapping, dict):
            continue
        for period_id, value in mapping.items():
            pid = _to_int(period_id, -1)
            if pid <= 0 or pid in out:
                continue
            if isinstance(value, list) and value:
                ts = value[0].get("date")
                if ts:
                    out[pid] = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone(et).date()
    return out


def _calendar_week_period_ids(schedule_payload: dict[str, Any], week: str, base_date: date | None = None) -> list[int]:
    period_dates = _scoring_period_dates(schedule_payload)
    if not period_dates:
        return []

    today = base_date or datetime.now(ZoneInfo("America/New_York")).date()
    this_monday = today - timedelta(days=today.weekday())
    week_monday = this_monday if week == "current" else this_monday + timedelta(days=7)
    week_sunday = week_monday + timedelta(days=6)
    return sorted(pid for pid, dt in period_dates.items() if week_monday <= dt <= week_sunday)


def _resolve_matchup_window(
    league_payload: dict[str, Any], schedule_payload: dict[str, Any], week: str
) -> tuple[int, list[int], int]:
    current_matchup = _current_matchup_period_id(league_payload)
    schedule_settings = (league_payload.get("settings") or {}).get("scheduleSettings", {})
    matchup_period_length = _to_int(schedule_settings.get("matchupPeriodLength"), 1)

    if matchup_period_length == 1:
        matchup_period_id = current_matchup if week == "current" else current_matchup + 1
        scoring_period_ids = _calendar_week_period_ids(schedule_payload, week)
        if scoring_period_ids:
            return matchup_period_id, scoring_period_ids, matchup_period_length

        target_matchup_period_ids = list(range(matchup_period_id, matchup_period_id + 7))
        scoring_period_ids = []
        for period_id in target_matchup_period_ids:
            period_scoring_ids = _matchup_scoring_period_ids(league_payload, period_id)
            if period_scoring_ids:
                scoring_period_ids.extend(period_scoring_ids)
            else:
                scoring_period_ids.append(period_id)
        return matchup_period_id, sorted(set(scoring_period_ids)), matchup_period_length

    matchup_period_id = current_matchup if week == "current" else current_matchup + 1
    scoring_period_ids = _matchup_scoring_period_ids(league_payload, matchup_period_id)
    if not scoring_period_ids:
        scoring_period_ids = [matchup_period_id]
    return matchup_period_id, sorted(set(scoring_period_ids)), matchup_period_length
