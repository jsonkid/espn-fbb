# espn-fbb

Minimal CLI for ESPN Fantasy Basketball analytics with deterministic JSON output.

## Quick Start

```bash
uv venv
uv sync
```

Create `~/.config/espn-fbb/config.toml`:

```toml
league_id = "123456"
team_id = "4"
season = 2026
espn_s2 = "COOKIE"
swid = "{SWID}"
```

Run:

```bash
uv run espn-fbb recap
uv run espn-fbb matchup preview
uv run espn-fbb matchup outlook
```

## Development

Install dev dependencies:

```bash
uv sync --extra dev
```

## Documentation

- User command reference: `docs/COMMANDS.md`
- Output contracts: `docs/OUTPUT_SCHEMA.md`
- Architecture: `docs/ARCHITECTURE.md`
- ESPN integration details: `docs/API_INTEGRATION.md`
- Analytics logic: `docs/ANALYTICS_METHOD.md`
- Cache/performance behavior: `docs/CACHE_AND_PERFORMANCE.md`
- Testing guide: `docs/TESTING.md`
- Changelog: `docs/CHANGELOG.md`
- Roadmap: `docs/ROADMAP.md`
- Docs index: `docs/README.md`
