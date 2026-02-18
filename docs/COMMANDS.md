# Commands

## Configuration

Default config file:

- `~/.config/espn-fbb/config.toml`

Required keys:

- `league_id` (string)
- `team_id` (integer)
- `season` (integer)

Optional private-league keys:

- `espn_s2`
- `swid`

Global overrides:

- `--league-id`
- `--team-id`
- `--season`
- `--no-cache`

## `espn-fbb recap`

Purpose:

- Summarize current matchup state and previous-day performance data for players who logged stats.

Examples:

```bash
espn-fbb recap
espn-fbb recap --league-id 233477 --team-id 1 --season 2026
```

## `espn-fbb matchup preview`

Purpose:

- Project next matchup using season-long player averages and projected starter games.

Examples:

```bash
espn-fbb matchup preview
espn-fbb matchup preview --no-cache
```

## `espn-fbb matchup outlook`

Purpose:

- Combine current matchup totals with projected remaining matchup performance.

Examples:

```bash
espn-fbb matchup outlook
espn-fbb matchup outlook --no-cache
```

## Exit Codes

- `0`: success
- `2`: config or argument error
- `3`: authentication error
- `4`: ESPN/network/request-budget error
- `5`: unexpected runtime error
