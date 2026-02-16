# ESPN API Integration

Last verified: 2026-02-16

ESPN’s fantasy API is unofficial and may change without notice.

## Hosts

Primary:

- `https://fantasy.espn.com/apis/v3/games/fba`

Fallback on first-host `403`:

- `https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba`

## Authentication

Private leagues use cookies:

- `espn_s2`
- `SWID`

Common auth failures return `401` or `403`.

## Endpoints

League payload:

- `/seasons/{season}/segments/0/leagues/{league_id}`

Pro team schedules:

- `/seasons/{season}?view=proTeamSchedules_wl`

Not used by current CLI:

- `/seasons/{season}/players`

Legacy/older schema paths (for example `leagueHistory`) are not supported by this tool.

## Views Used

- `mMatchupScore`
- `mScoreboard`
- `mTeam`
- `mRoster`
- `mSettings`
- `mMatchup`

## Request Policy

- Retry once on `403` by switching from primary host to fallback host.
- Do not retry non-403 responses.
- Parse JSON; reject invalid JSON response bodies.
- Use `x-fantasy-filter` for matchup-period targeting when needed.

Example `x-fantasy-filter` payload:

```json
{
  "schedule": {
    "filterMatchupPeriodIds": {
      "value": [17]
    }
  }
}
```

## Payload Variants Handled

1. Pro-team schedule location:
- top-level `proTeams`
- `settings.proTeams`

2. `proGamesByScoringPeriod` encodings:
- scalar count
- list of game objects
- nested dict (`value`, `gameCount`, nested children)
- list-indexed period counts

3. `settings.scheduleSettings.matchupPeriods` shapes:
- matchup-period keyed map/list
- scoring-period keyed map with matchup-period lists (inverted lookup required)

## Practical Notes

- Daily-matchup leagues (`matchupPeriodLength=1`) are treated as calendar-week windows for preview/outlook projections.
- Future matchup rows can be sparse; schedule-based game projection remains available even when matchup stat rows are minimal.
