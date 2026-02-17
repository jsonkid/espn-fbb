# espn-fbb

Minimal CLI for ESPN Fantasy Basketball analytics with deterministic JSON output.

## Quick Start

```bash
uv venv
uv sync --no-editable
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
espn-fbb recap
espn-fbb matchup preview
espn-fbb matchup outlook
```

## Development

Install dev dependencies (non-editable by default):

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
