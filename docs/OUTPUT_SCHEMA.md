# Output Schema

Current schema version for matchup commands: `2.0`.

All commands return JSON only.

## Recap Response

Top-level fields:

- `generated_at`, `league_id`, `team_id`, `you_team_name`, `opp_team_id`, `opp_team_name`, `matchup_period_id`
- `matchup_score` (`you`, `opp`)
- `categories` (array of 9 category rows)
- `movers` (up to 5)
- `candidates` (`you_good`, `you_bad`, `opp_good`, `opp_bad`)
- `candidates_meta` (`source_scoring_period_id`, `has_data`, `note`)
- `active_players` (`you`, `opp`)

Category row (`categories[]`):

- `key`, `you`, `opp`, `margin`, `status`

## Matchup Preview Response

Top-level fields:

- `schema_version`, `command`
- `generated_at`, `league_id`, `team_id`, `you_team_name`, `opp_team_id`, `opp_team_name`, `matchup_period_id`
- `you_standing`, `opp_standing`
- `projected_matchup_score` (`you`, `opp`, `tie`)
- `categories` (map keyed by category code)
- `games` (`you_total_games`, `opp_total_games`, `games_diff`)
- `lineup_actions` (structured actions)
- `summary_hints`
- `data_quality`
- `outlook` (`label`, `reason`)

Category entry (`categories.{CAT}`):

- `projected_you`, `projected_opp`, `projected_margin`
- `projected_status` (`you|opp|tie`)
- `projected_pdiff`
- `projected_signal` (`favored|at_risk|neutral`)

Lineup action entry:

- `type` (currently `swap`)
- `out_player_id`, `out_player_name`
- `in_player_id`, `in_player_name`
- `games_delta`
- `category_deltas` (keys: `PTS`, `3PM`, `REB`, `AST`, `STL`, `BLK`, `TO`)
- `score`

## Matchup Outlook Response

Top-level fields:

- `schema_version`, `command`
- `generated_at`, `league_id`, `team_id`, `you_team_name`, `opp_team_id`, `opp_team_name`, `matchup_period_id`
- `you_standing`, `opp_standing`
- `current_matchup_score` (`you`, `opp`, `tie`)
- `projected_matchup_score` (`you`, `opp`, `tie`)
- `categories` (map keyed by category code with paired `current_*` and `projected_*`)
- `games_remaining` (`you_remaining_games`, `opp_remaining_games`, `games_remaining_diff`)
- `summary_hints`
- `data_quality`
- `outlook` (`label`, `reason`)

Category entry (`categories.{CAT}`):

- `current_you`, `current_opp`, `current_margin`, `current_status`, `current_pdiff`, `current_signal`
- `projected_you`, `projected_opp`, `projected_margin`, `projected_status`, `projected_pdiff`, `projected_signal`

## Shared Objects

`TeamStanding`:

- `rank`
- `wins`, `losses`, `ties`
- `percentage`

`summary_hints`:

- `closest_categories`
- `biggest_advantages`
- `biggest_disadvantages`
- `swing_categories`

`data_quality`:

- `projection_basis`
- `projection_used`
- `season_id`
- `scoring_period_ids`
- `your_starters_missing_season_stats`
- `opp_starters_missing_season_stats`

## Stability Notes

- New top-level fields may be added in future versions.
- Existing fields keep semantic compatibility within a schema version.
- Consumers should branch logic using `schema_version` and `command`.

## Example: Matchup Preview JSON

Source: sanitized real output (`preview.json`).

```json
{
  "schema_version": "2.0",
  "command": "matchup_preview",
  "generated_at": "2026-02-16T13:29:21-05:00",
  "league_id": "233477",
  "team_id": 1,
  "you_team_name": "Example You",
  "opp_team_id": 2,
  "opp_team_name": "Example Opp",
  "you_standing": { "rank": 2, "wins": 12, "losses": 4, "ties": 0, "percentage": 0.75 },
  "opp_standing": { "rank": 6, "wins": 7, "losses": 9, "ties": 0, "percentage": 0.4375 },
  "matchup_period_id": 18,
  "projected_matchup_score": {
    "you": 5,
    "opp": 4,
    "tie": 0
  },
  "categories": {
    "FG%": {
      "projected_you": 0.4655,
      "projected_opp": 0.4702,
      "projected_margin": -0.0047,
      "projected_status": "opp",
      "projected_pdiff": -0.01,
      "projected_signal": "neutral"
    },
    "FT%": {
      "projected_you": 0.8444,
      "projected_opp": 0.8452,
      "projected_margin": -0.0009,
      "projected_status": "opp",
      "projected_pdiff": -0.0009,
      "projected_signal": "neutral"
    },
    "3PM": {
      "projected_you": 67.6348,
      "projected_opp": 49.3321,
      "projected_margin": 18.3027,
      "projected_status": "you",
      "projected_pdiff": 0.371,
      "projected_signal": "favored"
    },
    "REB": {
      "projected_you": 180.8684,
      "projected_opp": 162.4024,
      "projected_margin": 18.466,
      "projected_status": "you",
      "projected_pdiff": 0.1137,
      "projected_signal": "favored"
    },
    "AST": {
      "projected_you": 166.3506,
      "projected_opp": 118.796,
      "projected_margin": 47.5546,
      "projected_status": "you",
      "projected_pdiff": 0.4003,
      "projected_signal": "favored"
    },
    "STL": {
      "projected_you": 41.678,
      "projected_opp": 28.8121,
      "projected_margin": 12.8659,
      "projected_status": "you",
      "projected_pdiff": 0.4465,
      "projected_signal": "favored"
    },
    "BLK": {
      "projected_you": 22.0811,
      "projected_opp": 22.7464,
      "projected_margin": -0.6653,
      "projected_status": "opp",
      "projected_pdiff": -0.0292,
      "projected_signal": "neutral"
    },
    "TO": {
      "projected_you": 72.8604,
      "projected_opp": 62.8591,
      "projected_margin": 10.0013,
      "projected_status": "opp",
      "projected_pdiff": -0.1591,
      "projected_signal": "at_risk"
    },
    "PTS": {
      "projected_you": 653.2792,
      "projected_opp": 482.4833,
      "projected_margin": 170.7959,
      "projected_status": "you",
      "projected_pdiff": 0.354,
      "projected_signal": "favored"
    }
  },
  "games": {
    "you_total_games": 34,
    "opp_total_games": 32,
    "games_diff": 2
  },
  "lineup_actions": [],
  "summary_hints": {
    "closest_categories": [
      "FT%",
      "FG%",
      "BLK"
    ],
    "biggest_advantages": [
      "PTS",
      "AST",
      "REB"
    ],
    "biggest_disadvantages": [
      "BLK",
      "FG%",
      "FT%"
    ],
    "swing_categories": []
  },
  "data_quality": {
    "projection_basis": "season_avg_x_projected_games",
    "projection_used": true,
    "season_id": 2026,
    "scoring_period_ids": [
      126,
      127,
      128,
      129,
      130,
      131,
      132
    ],
    "your_starters_missing_season_stats": 0,
    "opp_starters_missing_season_stats": 0
  },
  "outlook": {
    "label": "Lean You",
    "reason": "Favored in 4 cats; +2 games"
  }
}
```

## Example: Matchup Outlook JSON

Source: sanitized real output (`outlook.json`).

```json
{
  "schema_version": "2.0",
  "command": "matchup_outlook",
  "generated_at": "2026-02-16T13:27:25-05:00",
  "league_id": "233477",
  "team_id": 1,
  "you_team_name": "Example You",
  "opp_team_id": 2,
  "opp_team_name": "Example Opp",
  "you_standing": { "rank": 2, "wins": 12, "losses": 4, "ties": 0, "percentage": 0.75 },
  "opp_standing": { "rank": 6, "wins": 7, "losses": 9, "ties": 0, "percentage": 0.4375 },
  "matchup_period_id": 17,
  "current_matchup_score": {
    "you": 4,
    "opp": 4,
    "tie": 1
  },
  "projected_matchup_score": {
    "you": 6,
    "opp": 3,
    "tie": 0
  },
  "categories": {
    "FG%": {
      "current_you": 0.4266,
      "current_opp": 0.4747,
      "current_margin": -0.0481,
      "current_status": "opp",
      "current_pdiff": -0.1013,
      "current_signal": "at_risk",
      "projected_you": 0.4529,
      "projected_opp": 0.4669,
      "projected_margin": -0.014,
      "projected_status": "opp",
      "projected_pdiff": -0.03,
      "projected_signal": "neutral"
    },
    "FT%": {
      "current_you": 0.8788,
      "current_opp": 0.7937,
      "current_margin": 0.0851,
      "current_status": "you",
      "current_pdiff": 0.1072,
      "current_signal": "favored",
      "projected_you": 0.8544,
      "projected_opp": 0.7891,
      "projected_margin": 0.0653,
      "projected_status": "you",
      "projected_pdiff": 0.0828,
      "projected_signal": "neutral"
    },
    "3PM": {
      "current_you": 20.0,
      "current_opp": 32.0,
      "current_margin": -12.0,
      "current_status": "opp",
      "current_pdiff": -0.375,
      "current_signal": "at_risk",
      "projected_you": 65.7331,
      "projected_opp": 76.1498,
      "projected_margin": -10.4168,
      "projected_status": "opp",
      "projected_pdiff": -0.1368,
      "projected_signal": "at_risk"
    },
    "REB": {
      "current_you": 80.0,
      "current_opp": 62.0,
      "current_margin": 18.0,
      "current_status": "you",
      "current_pdiff": 0.2903,
      "current_signal": "favored",
      "projected_you": 207.2903,
      "projected_opp": 180.8697,
      "projected_margin": 26.4206,
      "projected_status": "you",
      "projected_pdiff": 0.1461,
      "projected_signal": "favored"
    },
    "AST": {
      "current_you": 60.0,
      "current_opp": 66.0,
      "current_margin": -6.0,
      "current_status": "opp",
      "current_pdiff": -0.0909,
      "current_signal": "neutral",
      "projected_you": 162.9286,
      "projected_opp": 156.0546,
      "projected_margin": 6.874,
      "projected_status": "you",
      "projected_pdiff": 0.044,
      "projected_signal": "neutral"
    },
    "STL": {
      "current_you": 14.0,
      "current_opp": 13.0,
      "current_margin": 1.0,
      "current_status": "you",
      "current_pdiff": 0.0769,
      "current_signal": "neutral",
      "projected_you": 44.1794,
      "projected_opp": 38.6046,
      "projected_margin": 5.5748,
      "projected_status": "you",
      "projected_pdiff": 0.1444,
      "projected_signal": "favored"
    },
    "BLK": {
      "current_you": 7.0,
      "current_opp": 7.0,
      "current_margin": 0.0,
      "current_status": "tie",
      "current_pdiff": 0.0,
      "current_signal": "neutral",
      "projected_you": 21.7747,
      "projected_opp": 18.3568,
      "projected_margin": 3.4179,
      "projected_status": "you",
      "projected_pdiff": 0.1862,
      "projected_signal": "favored"
    },
    "TO": {
      "current_you": 27.0,
      "current_opp": 28.0,
      "current_margin": -1.0,
      "current_status": "you",
      "current_pdiff": 0.0357,
      "current_signal": "neutral",
      "projected_you": 74.8451,
      "projected_opp": 73.0209,
      "projected_margin": 1.8242,
      "projected_status": "opp",
      "projected_pdiff": -0.025,
      "projected_signal": "neutral"
    },
    "PTS": {
      "current_you": 264.0,
      "current_opp": 270.0,
      "current_margin": -6.0,
      "current_status": "opp",
      "current_pdiff": -0.0222,
      "current_signal": "neutral",
      "projected_you": 706.7756,
      "projected_opp": 641.6681,
      "projected_margin": 65.1074,
      "projected_status": "you",
      "projected_pdiff": 0.1015,
      "projected_signal": "favored"
    }
  },
  "games_remaining": {
    "you_remaining_games": 24,
    "opp_remaining_games": 24,
    "games_remaining_diff": 0
  },
  "summary_hints": {
    "closest_categories": [
      "FG%",
      "FT%",
      "TO"
    ],
    "biggest_advantages": [
      "PTS",
      "REB",
      "AST"
    ],
    "biggest_disadvantages": [
      "3PM",
      "FG%",
      "TO"
    ],
    "swing_categories": [
      "AST",
      "BLK",
      "TO",
      "PTS"
    ]
  },
  "data_quality": {
    "projection_basis": "current_totals_plus_remaining_season_avg_x_projected_games",
    "projection_used": true,
    "season_id": 2026,
    "scoring_period_ids": [
      122,
      123,
      124,
      125
    ],
    "your_starters_missing_season_stats": 0,
    "opp_starters_missing_season_stats": 0
  },
  "outlook": {
    "label": "Lean You",
    "reason": "Favored in 4 cats; +0 games"
  }
}
```

## Example: Recap JSON

Source: sanitized real output (`recap.json`).

```json
{
  "generated_at": "2026-02-16T09:05:10-05:00",
  "league_id": "233477",
  "team_id": 1,
  "you_team_name": "Example You",
  "opp_team_id": 2,
  "opp_team_name": "Example Opp",
  "matchup_period_id": 17,
  "matchup_score": {
    "you": 4,
    "opp": 4
  },
  "categories": [
    { "key": "FG%", "you": 0.4266, "opp": 0.4747, "margin": -0.0481, "status": "opp" },
    { "key": "FT%", "you": 0.8788, "opp": 0.7937, "margin": 0.0851, "status": "you" },
    { "key": "3PM", "you": 20.0, "opp": 32.0, "margin": -12.0, "status": "opp" },
    { "key": "REB", "you": 80.0, "opp": 62.0, "margin": 18.0, "status": "you" },
    { "key": "AST", "you": 60.0, "opp": 66.0, "margin": -6.0, "status": "opp" },
    { "key": "STL", "you": 14.0, "opp": 13.0, "margin": 1.0, "status": "you" },
    { "key": "BLK", "you": 7.0, "opp": 7.0, "margin": 0.0, "status": "tie" },
    { "key": "TO", "you": 27.0, "opp": 28.0, "margin": -1.0, "status": "you" },
    { "key": "PTS", "you": 264.0, "opp": 270.0, "margin": -6.0, "status": "opp" }
  ],
  "movers": [],
  "candidates": {
    "you_good": [],
    "you_bad": [],
    "opp_good": [],
    "opp_bad": []
  },
  "candidates_meta": {
    "source_scoring_period_id": 121,
    "has_data": false,
    "note": "No completed games in previous scoring day; notable performances unavailable."
  },
  "active_players": {
    "you": 10,
    "opp": 10
  }
}
```
