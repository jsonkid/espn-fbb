# Changelog

## February 17, 2026

- Migrated from `pip` to `uv`

## February 16, 2026

- Refactored matchup command surface:
  - `espn-fbb matchup preview`
  - `espn-fbb matchup outlook`
- Added outlook model combining current matchup totals and projected remaining performance.
- Upgraded matchup response schema to `2.0`:
  - canonical per-category maps
  - structured lineup actions
  - `summary_hints`
  - `data_quality`
- Removed old preview week selector path from user command surface.
- Reorganized documentation into audience-specific files.

