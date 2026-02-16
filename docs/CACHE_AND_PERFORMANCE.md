# Cache And Performance

## Cache Location

- `~/.cache/espn-fbb/`

Cache files are JSON blobs keyed by SHA-256 of logical cache keys.

## TTL Defaults

- League payload (`get_league`): 3 hours
- Pro-team schedules (`get_pro_team_schedules`): 24 hours
- Recap snapshots retained: 10 days

## Snapshot Keys

Format:

- `snapshot:{league_id}:{team_id}:{matchup_period_id}:{et_date}`

Used for day-over-day mover comparisons in `recap`.

## Request Budgets

Per command process defaults:

- max ESPN league requests: `2`
- max schedule requests: `1`

Exceeding budget raises `RequestLimitError` and exits with code `4`.

## Efficiency Notes

- Cache lookup is attempted before network request when enabled.
- `--no-cache` bypasses reads/writes for fresh pulls.
- View lists are command-specific to avoid over-fetching.
- Schedule parsing is tolerant to payload shape drift to reduce re-fetch/retry churn.

