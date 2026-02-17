# Testing

## Run Tests

```bash
uv sync --extra dev --no-editable
uv run pytest -q
```

## Test Layout

- `tests/test_fetch.py`
  - host fallback behavior
  - auth failures
  - request budget enforcement
  - caching behavior
- `tests/test_analytics.py`
  - recap movers/candidates
  - previous-day handling
  - matchup preview/outlook projections
  - payload shape variants for schedule/matchup mappings
- `tests/test_cli.py`
  - command wiring
  - JSON output contract smoke tests

## Fixture Strategy

- Use small synthetic payloads with only required keys.
- Cover ESPN shape variants explicitly (dict/list/nested schedule maps).
- Assert behavior-level outcomes rather than overfitting exact internals.

## Regression Guidance

When changing schema:

1. update `docs/OUTPUT_SCHEMA.md`
2. update corresponding schema models
3. update CLI and analytics tests

When changing fetch behavior:

1. add tests for host/auth/error branching
2. verify cache hit and no-cache paths
