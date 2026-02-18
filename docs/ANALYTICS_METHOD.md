# Analytics Method

This project uses deterministic category math only.

## Categories

Order:

- `FG%`, `FT%`, `3PM`, `REB`, `AST`, `STL`, `BLK`, `TO`, `PTS`

Status logic:

- Most categories: higher is better
- `TO`: lower is better
- Equal values are `tie`

## Recap

- Uses current matchup totals from league payload.
- Computes per-category margin and status.
- Computes movers versus yesterday snapshot with category thresholds.
- Notable performances use previous completed scoring period only.
- If no previous-day stats exist, recap rosters are empty and explained via metadata.

## Matchup Preview

- Projects next matchup from season totals converted to per-game averages.
- Uses projected starter entries (bench can replace `OUT` starters).
- Starter slots come from `rosterSettings.lineupSlotCounts`.
- Projects team totals:
  - counting categories: per-game * projected games
  - percentages: recomputed from projected made/attempted totals
- Builds projected category signals:
  - `favored` if `pdiff >= 0.10`
  - `at_risk` if `pdiff <= -0.10`
  - otherwise `neutral`
- Builds optional structured lineup swap actions using simple heuristics.

## Matchup Outlook

- Uses current matchup totals for current state.
- Computes remaining scoring periods in current matchup window.
- Projects remaining starter production from season averages.
- Adds current totals + projected remaining totals to get projected final totals.
- Recomputes category statuses/signals from projected final totals.

## Outlook Label

- `Strong Lean You`: strong category edge and games edge
- `Lean You`: mild category edge
- `Toss-up`: neutral
- `Lean Opponent` / `Strong Lean Opponent`: mirrored logic

Reason string format:

- `"Favored in {N} cats; {+/-G} games"`

## Data Quality Metadata

Each matchup response includes:

- projection basis string
- whether projection signal was usable
- selected season id
- relevant scoring period ids
- missing season-stat counts among projected starters (you/opp)
