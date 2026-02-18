# Architecture

## Design Goals

- Deterministic analytics only
- Minimal ESPN API usage
- JSON-first output contracts
- Reliable behavior on low-resource devices

## Module Responsibilities

- `espn_fbb/cli.py`
  - Typer CLI entrypoints
  - Config loading and error-to-exit-code mapping
  - Orchestrates fetch + analytics
- `espn_fbb/config.py`
  - Loads and validates TOML config
- `espn_fbb/fetch.py`
  - ESPN HTTP client
  - Auth cookies, host fallback, request budgets
  - Cache integration
- `espn_fbb/cache.py`
  - Filesystem JSON cache (hash-based keys)
  - Snapshot key helpers
- `espn_fbb/analytics.py`
  - Orchestrates recap/preview/outlook assembly
  - Contains recap-specific roster/performance and mover logic
- `espn_fbb/analytics_base.py`
  - Core category/stat constants and low-level stat extraction helpers
  - Category status/signal math and category-map shaping helpers
- `espn_fbb/analytics_schedule.py`
  - Matchup/scoring-period resolution
  - Pro-team game-count normalization across ESPN payload variants
  - Starter slot derivation from league settings
- `espn_fbb/analytics_projection.py`
  - Starter selection and projected games logic
  - Season-average projection math and lineup swap heuristics
  - Projection metadata helpers (`season_id`, missing-stat counts)
- `espn_fbb/schema.py`
  - Pydantic response models
- `espn_fbb/utils.py`
  - ET time helpers and ISO timestamp helpers

## Runtime Flow

1. CLI command resolves config and overrides.
2. Fetch layer requests league payload + pro-team schedules as needed.
3. Fetch layer normalizes host/auth/retry behavior and applies cache TTL.
4. Analytics layer computes deterministic response objects.
5. CLI emits model JSON to stdout.

## Analytics Boundaries

High-level command analytics should enter through:

- `build_recap(...)` in `espn_fbb/analytics.py`
- `build_preview(...)` in `espn_fbb/analytics.py`
- `build_outlook(...)` in `espn_fbb/analytics.py`

Internal helper ownership:

- Base stat/category helpers: `analytics_base.py`
- Schedule/window/game-map helpers: `analytics_schedule.py`
- Projection/lineup helpers: `analytics_projection.py`

Boundary rule:

- Keep cross-module dependencies one-way where practical:
  - `analytics.py` imports helper modules.
  - Helper modules avoid importing `analytics.py`.

## Error Handling

- Config or argument issues -> exit `2`
- Auth failures (`401`/`403`) -> exit `3`
- ESPN/network/request-budget failures -> exit `4`
- Unexpected runtime exceptions -> exit `5`
