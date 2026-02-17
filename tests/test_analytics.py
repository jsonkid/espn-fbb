from __future__ import annotations

from espn_fbb.analytics import _lineup_swap_actions, build_outlook, build_preview, build_recap, build_snapshot
from espn_fbb.schema import CategorySignal, CategoryStat


def _league_payload() -> dict:
    return {
        "status": {"currentMatchupPeriod": 5, "currentScoringPeriod": 80},
        "schedule": [
            {
                "matchupPeriodId": 5,
                "home": {
                    "teamId": 4,
                    "cumulativeScore": {
                        "scoreByStat": {
                            "19": 0.47,
                            "20": 0.82,
                            "17": 52,
                            "6": 310,
                            "3": 230,
                            "2": 38,
                            "1": 26,
                            "11": 96,
                            "0": 980,
                        }
                    },
                },
                "away": {
                    "teamId": 7,
                    "cumulativeScore": {
                        "scoreByStat": {
                            "19": 0.45,
                            "20": 0.79,
                            "17": 46,
                            "6": 290,
                            "3": 210,
                            "2": 36,
                            "1": 22,
                            "11": 102,
                            "0": 930,
                        }
                    },
                },
            }
        ],
        "teams": [
            {
                "id": 4,
                "location": "Test",
                "nickname": "Alpha",
                "roster": {
                    "entries": [
                        {
                            "lineupSlotId": 0,
                            "playerPoolEntry": {
                                "player": {
                                    "id": 100,
                                    "fullName": "Alpha One",
                                    "proTeamId": 1,
                                    "injuryStatus": "ACTIVE",
                                    "stats": [
                                        {
                                            "statSourceId": 0,
                                            "scoringPeriodId": 80,
                                            "stats": {
                                                "0": 28,
                                                "17": 5,
                                                "6": 11,
                                                "3": 9,
                                                "2": 3,
                                                "1": 1,
                                                "11": 2,
                                                "13": 10,
                                                "14": 18,
                                                "15": 5,
                                                "16": 6,
                                            },
                                        }
                                    ],
                                }
                            },
                        },
                        {
                            "lineupSlotId": 1,
                            "playerPoolEntry": {
                                "player": {
                                    "id": 101,
                                    "fullName": "Beta Two",
                                    "proTeamId": 2,
                                    "injuryStatus": "OUT",
                                    "stats": [
                                        {
                                            "statSourceId": 0,
                                            "scoringPeriodId": 80,
                                            "stats": {
                                                "0": 8,
                                                "11": 6,
                                                "13": 3,
                                                "14": 12,
                                                "15": 2,
                                                "16": 7,
                                            },
                                        }
                                    ],
                                }
                            },
                        },
                    ]
                },
            },
            {
                "id": 7,
                "location": "Test",
                "nickname": "Beta",
                "roster": {
                    "entries": [
                        {
                            "lineupSlotId": 0,
                            "playerPoolEntry": {
                                "player": {
                                    "id": 200,
                                    "fullName": "Gamma Opp",
                                    "proTeamId": 3,
                                    "injuryStatus": "ACTIVE",
                                    "stats": [
                                        {
                                            "statSourceId": 0,
                                            "scoringPeriodId": 80,
                                            "stats": {
                                                "0": 21,
                                                "17": 4,
                                                "6": 8,
                                                "3": 4,
                                                "2": 1,
                                                "1": 0,
                                                "11": 5,
                                                "13": 6,
                                                "14": 16,
                                                "15": 4,
                                                "16": 8,
                                            },
                                        }
                                    ],
                                }
                            },
                        }
                    ]
                },
            },
        ],
    }


def _schedule_payload() -> dict:
    return {
        "proTeams": [
            {"id": 1, "proGamesByMatchupPeriod": {"5": 4, "6": 3}},
            {"id": 2, "proGamesByMatchupPeriod": {"5": 3, "6": 4}},
            {"id": 3, "proGamesByMatchupPeriod": {"5": 3, "6": 2}},
        ]
    }


def test_build_recap_and_movers_with_ties_allowed():
    league = _league_payload()
    league["status"]["currentScoringPeriod"] = 81  # previous day is 80 in fixture rows
    recap = build_recap(league, team_id=4, league_id="123")
    snapshot = build_snapshot(recap.categories)

    # simulate yesterday with one tied category and a large move
    snapshot["3PM"] = {"you": 44, "opp": 44}

    recap2 = build_recap(league, team_id=4, league_id="123", yesterday_snapshot=snapshot)

    assert recap2.matchup_score["you"] > recap2.matchup_score["opp"]
    assert any(m.key == "3PM" for m in recap2.movers)
    assert recap2.candidates.you_good
    assert recap2.candidates.you_bad


def test_build_preview_signals_and_outlook():
    preview = build_preview(
        league_payload=_league_payload(),
        schedule_payload=_schedule_payload(),
        team_id=4,
        league_id="123",
        week="current",
    )

    assert preview.games.games_diff > 0
    assert preview.schema_version == "2.0"
    assert preview.command == "matchup_preview"
    assert set(preview.projected_matchup_score.keys()) == {"you", "opp", "tie"}
    assert set(preview.categories.keys()) == {"FG%", "FT%", "3PM", "REB", "AST", "STL", "BLK", "TO", "PTS"}
    assert preview.outlook["label"] in {"Lean You", "Strong Lean You"}
    assert preview.data_quality.projection_basis
    assert preview.summary_hints.closest_categories


def test_preview_next_has_no_lineup_actions():
    preview = build_preview(
        league_payload=_league_payload(),
        schedule_payload=_schedule_payload(),
        team_id=4,
        league_id="123",
        week="next",
    )
    assert preview.lineup_actions == []


def test_build_outlook_includes_current_and_projected_sections():
    league = _league_payload()
    league["status"]["currentScoringPeriod"] = 81
    outlook = build_outlook(
        league_payload=league,
        schedule_payload=_schedule_payload(),
        team_id=4,
        league_id="123",
    )

    assert set(outlook.current_matchup_score.keys()) == {"you", "opp", "tie"}
    assert set(outlook.projected_matchup_score.keys()) == {"you", "opp", "tie"}
    assert outlook.schema_version == "2.0"
    assert outlook.command == "matchup_outlook"
    assert set(outlook.categories.keys()) == {"FG%", "FT%", "3PM", "REB", "AST", "STL", "BLK", "TO", "PTS"}
    assert isinstance(outlook.games_remaining.games_remaining_diff, int)
    assert isinstance(outlook.summary_hints.swing_categories, list)
    assert outlook.data_quality.projection_basis


def test_build_outlook_handles_missing_matchup_row():
    league = _league_payload()
    league["status"]["currentMatchupPeriod"] = 6
    # Keep schedule rows that do not include matchupPeriodId=6 for this team.
    league["schedule"] = [league["schedule"][0]]

    outlook = build_outlook(
        league_payload=league,
        schedule_payload=_schedule_payload(),
        team_id=4,
        league_id="123",
    )

    assert outlook.matchup_period_id == 6
    assert outlook.current_matchup_score == {"you": 0, "opp": 0, "tie": 9}


def test_lineup_swap_actions_handles_sort_ties():
    def _entry(player_id: int, name: str, pro_team_id: int, lineup_slot_id: int, pts_total: float, reb_total: float) -> dict:
        return {
            "lineupSlotId": lineup_slot_id,
            "playerPoolEntry": {
                "player": {
                    "id": player_id,
                    "fullName": name,
                    "proTeamId": pro_team_id,
                    "injuryStatus": "ACTIVE",
                    "stats": [
                        {
                            "statSourceId": 0,
                            "statSplitTypeId": 0,
                            "seasonId": 2026,
                            "scoringPeriodId": 0,
                            "stats": {
                                "0": pts_total,
                                "6": reb_total,
                                "11": 10,
                                "42": 10,
                            },
                        }
                    ],
                }
            },
        }

    team = {
        "roster": {
            "entries": [
                _entry(1, "Starter A", 1, 0, 100, 50),
                _entry(2, "Bench B", 2, 12, 200, 100),
                _entry(3, "Bench C", 3, 12, 200, 100),
            ]
        }
    }
    pro_team_games = {1: 1, 2: 3, 3: 3}
    starter_slot_counts = {0: 1}
    categories = [
        CategoryStat(key="PTS", you=100.0, opp=110.0, margin=-10.0, status="opp"),
        CategoryStat(key="REB", you=40.0, opp=50.0, margin=-10.0, status="opp"),
        CategoryStat(key="TO", you=20.0, opp=15.0, margin=5.0, status="opp"),
    ]
    at_risk = [
        CategorySignal(key="PTS", pdiff=-0.1),
        CategorySignal(key="REB", pdiff=-0.1),
    ]

    actions = _lineup_swap_actions(
        team=team,
        season_id=2026,
        pro_team_games=pro_team_games,
        starter_slot_counts=starter_slot_counts,
        categories=categories,
        at_risk=at_risk,
    )

    assert actions
    assert actions[0].in_player_id == 2
    assert all(a.type == "swap" for a in actions)


def test_build_preview_handles_list_game_values():
    schedule_payload = {
        "proTeams": [
            {"id": 1, "proGamesByMatchupPeriod": {"5": [{"matchupPeriodId": 5}, {"matchupPeriodId": 5}]}},
            {"id": 2, "proGamesByMatchupPeriod": {"5": [1, 2, 3]}},
            {"id": 3, "proGamesByMatchupPeriod": {"5": []}},
        ]
    }

    preview = build_preview(
        league_payload=_league_payload(),
        schedule_payload=schedule_payload,
        team_id=4,
        league_id="123",
        week="current",
    )

    assert isinstance(preview.games.games_diff, int)


def test_recap_candidates_use_previous_scoring_day():
    league = _league_payload()
    league["status"]["currentScoringPeriod"] = 80

    # Player has huge current-day line (80) but only modest previous-day line (79).
    # Recap notable performances should use previous day (79), so this player should
    # not appear as a good candidate.
    your_entries = league["teams"][0]["roster"]["entries"]
    your_entries[0]["playerPoolEntry"]["player"]["stats"] = [
        {
            "statSourceId": 0,
            "scoringPeriodId": 80,
            "stats": {"0": 35, "17": 6, "6": 12, "3": 10, "2": 4, "1": 3, "11": 2},
        },
        {
            "statSourceId": 0,
            "scoringPeriodId": 79,
            "stats": {"0": 12, "17": 1, "6": 4, "3": 3, "2": 0, "1": 0, "11": 1},
        },
    ]

    recap = build_recap(league, team_id=4, league_id="123")
    names = {p.player_name for p in recap.candidates.you_good}
    assert "Alpha One" not in names


def test_recap_candidates_do_not_fallback_to_aggregate_when_previous_missing():
    league = _league_payload()
    league["status"]["currentScoringPeriod"] = 80
    your_entries = league["teams"][0]["roster"]["entries"]

    # Aggregate-like row without scoringPeriodId should not be used for previous-day recap.
    your_entries[0]["playerPoolEntry"]["player"]["stats"] = [
        {
            "statSourceId": 0,
            "stats": {"0": 32, "17": 7, "6": 12, "3": 10, "2": 4, "1": 2, "11": 1},
        }
    ]

    recap = build_recap(league, team_id=4, league_id="123")
    names = {p.player_name for p in recap.candidates.you_good}
    assert "Alpha One" not in names


def test_recap_candidates_include_lineup_role_metadata():
    league = _league_payload()
    league["status"]["currentScoringPeriod"] = 81  # previous day is 80 in fixture rows
    recap = build_recap(league, team_id=4, league_id="123")
    assert recap.candidates.you_good
    assert recap.candidates.you_bad
    assert recap.candidates.you_good[0].lineup_role in {"starter", "bench"}
    assert isinstance(recap.candidates.you_good[0].lineup_slot_id, int)


def test_recap_no_previous_day_games_is_graceful():
    league = _league_payload()
    league["status"]["currentScoringPeriod"] = 81  # previous day is 80

    # Remove scoringPeriodId=80 rows to simulate no games yesterday.
    for team in league["teams"]:
        for entry in team["roster"]["entries"]:
            player = entry["playerPoolEntry"]["player"]
            player["stats"] = [
                {
                    "statSourceId": 0,
                    "scoringPeriodId": 79,
                    "stats": {"0": 10},
                }
            ]

    recap = build_recap(league, team_id=4, league_id="123")
    assert recap.candidates.you_good == []
    assert recap.candidates.you_bad == []
    assert recap.candidates.opp_good == []
    assert recap.candidates.opp_bad == []
    assert recap.candidates_meta.has_data is False
    assert recap.candidates_meta.source_scoring_period_id == 80
    assert recap.candidates_meta.note is not None


def test_preview_games_sum_scoring_periods_for_matchup():
    league = _league_payload()
    league["settings"] = {
        "scheduleSettings": {
            "matchupPeriods": {
                "6": {"start": 101, "end": 107},
            }
        }
    }

    schedule_payload = {
        "proTeams": [
            {"id": 1, "proGamesByScoringPeriod": {"101": 1, "102": 1, "103": 0, "104": 1, "105": 0, "106": 1, "107": 1}},
            {"id": 2, "proGamesByScoringPeriod": {"101": 1, "102": 0, "103": 1, "104": 1, "105": 0, "106": 0, "107": 1}},
            {"id": 3, "proGamesByScoringPeriod": {"101": 1, "102": 1, "103": 1, "104": 0, "105": 0, "106": 0, "107": 1}},
        ]
    }

    preview = build_preview(
        league_payload=league,
        schedule_payload=schedule_payload,
        team_id=4,
        league_id="123",
        week="next",
    )

    # Team 4 has pro teams 1 and 2 in fixture: (5 + 4) = 9 player-games.
    assert preview.games.you_total_games == 9


def test_preview_games_with_list_matchup_period_mapping():
    league = _league_payload()
    league["settings"] = {
        "scheduleSettings": {
            "matchupPeriods": {
                "6": [101, 102, 103],
            }
        }
    }
    schedule_payload = {
        "proTeams": [
            {"id": 1, "proGamesByScoringPeriod": {"101": 1, "102": 1, "103": 1}},
            {"id": 2, "proGamesByScoringPeriod": {"101": 0, "102": 1, "103": 1}},
            {"id": 3, "proGamesByScoringPeriod": {"101": 1, "102": 0, "103": 0}},
        ]
    }
    preview = build_preview(
        league_payload=league,
        schedule_payload=schedule_payload,
        team_id=4,
        league_id="123",
        week="next",
    )
    assert preview.games.you_total_games == 5


def test_preview_games_with_list_indexed_scoring_map():
    league = _league_payload()
    league["settings"] = {
        "scheduleSettings": {
            "matchupPeriods": {
                "6": [6, 7, 8],
            }
        }
    }
    schedule_payload = {
        "proTeams": [
            {"id": 1, "proGamesByScoringPeriod": [0, 0, 0, 0, 0, 0, 1, 1, 1]},
            {"id": 2, "proGamesByScoringPeriod": [0, 0, 0, 0, 0, 0, 1, 0, 1]},
            {"id": 3, "proGamesByScoringPeriod": [0, 0, 0, 0, 0, 0, 0, 1, 0]},
        ]
    }
    preview = build_preview(
        league_payload=league,
        schedule_payload=schedule_payload,
        team_id=4,
        league_id="123",
        week="next",
    )
    # With projected-starter replacement, this fixture resolves to 2.
    assert preview.games.you_total_games == 2


def test_preview_games_with_nested_dict_counts():
    league = _league_payload()
    league["settings"] = {
        "scheduleSettings": {
            "matchupPeriods": {
                "6": [101, 102, 103],
            }
        }
    }
    schedule_payload = {
        "proTeams": [
            {
                "id": 1,
                "proGamesByScoringPeriod": {
                    "101": {"a": 1, "b": 1},
                    "102": {"value": 1},
                    "103": {"gameCount": 1},
                },
            },
            {
                "id": 2,
                "proGamesByScoringPeriod": {
                    "101": {"x": 1},
                    "102": {"y": 0},
                    "103": {"z": 1},
                },
            },
            {"id": 3, "proGamesByScoringPeriod": {"101": 1, "102": 0, "103": 0}},
        ]
    }
    preview = build_preview(
        league_payload=league,
        schedule_payload=schedule_payload,
        team_id=4,
        league_id="123",
        week="next",
    )
    # Team 4 includes pro teams 1 and 2 in fixture: (4 + 2) = 6.
    assert preview.games.you_total_games == 6


def test_preview_prefers_scoring_period_bounds_over_generic_bounds():
    league = _league_payload()
    league["settings"] = {
        "scheduleSettings": {
            "matchupPeriods": {
                # Generic bounds point to matchup id, but scoring bounds contain real period range.
                "6": {
                    "start": 6,
                    "end": 6,
                    "startScoringPeriodId": 101,
                    "endScoringPeriodId": 103,
                }
            }
        }
    }
    schedule_payload = {
        "proTeams": [
            {"id": 1, "proGamesByScoringPeriod": {"101": 1, "102": 1, "103": 1}},
            {"id": 2, "proGamesByScoringPeriod": {"101": 0, "102": 1, "103": 1}},
            {"id": 3, "proGamesByScoringPeriod": {"101": 1, "102": 0, "103": 0}},
        ]
    }
    preview = build_preview(
        league_payload=league,
        schedule_payload=schedule_payload,
        team_id=4,
        league_id="123",
        week="next",
    )
    # Team 4 has pro teams 1 and 2 in fixture => (3 + 2) = 5.
    assert preview.games.you_total_games == 5


def test_preview_inverts_matchup_periods_when_keyed_by_scoring_period():
    league = _league_payload()
    league["settings"] = {
        "scheduleSettings": {
            # scoringPeriodId -> [matchupPeriodId]
            "matchupPeriods": {
                "101": [6],
                "102": [6],
                "103": [6],
                "104": [7],
            }
        }
    }
    schedule_payload = {
        "proTeams": [
            {"id": 1, "proGamesByScoringPeriod": {"101": 1, "102": 1, "103": 1, "104": 0}},
            {"id": 2, "proGamesByScoringPeriod": {"101": 0, "102": 1, "103": 1, "104": 1}},
            {"id": 3, "proGamesByScoringPeriod": {"101": 1, "102": 0, "103": 0, "104": 1}},
        ]
    }
    preview = build_preview(
        league_payload=league,
        schedule_payload=schedule_payload,
        team_id=4,
        league_id="123",
        week="next",
    )
    # Projected-starter replacement in this fixture resolves to 6.
    assert preview.games.you_total_games == 6
