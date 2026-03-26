# Weekend Scout -- Design Changes Log

Changes from the original design (docs/weekend-scout-mvp-design.md).

| Date | Design Section | Change | Reason |
|------|---------------|--------|--------|
| 2026-03-26 | 5.2 SKILL.md | Added `disable-model-invocation: true` | Prevent auto-triggering during unrelated work |
| 2026-03-26 | 6. Project Structure | Skill lives in project .claude/ not ~/.claude/ | Keeps everything version-controlled together |
| 2026-03-26 | 4.1 Config | Using `platformdirs` for cross-platform config path | Windows compatibility (AppData vs ~/.weekend-scout) |
| 2026-03-26 | 5.2 SKILL.md | Removed `cd ~/weekend-scout &&` prefix from all CLI calls in SKILL.md | Package is installed via pip; `python -m weekend_scout` works from any directory |
| 2026-03-26 | 4.2 cities.py | `parse_geonames_file` returns `name_local` (native name) in addition to documented keys | Required by city list cache schema; also needed for local-script search queries |
| 2026-03-26 | 4.2 cities.py | `download_geonames` resolves `data/` via `Path(__file__)` rather than a fixed path | Works correctly in both editable install and when invoked from any working directory |
| 2026-03-26 | 4.2 cities.py | Query generation functions accept ISO date strings, not datetime objects as in design pseudocode | Consistent with CLI contract; avoids date object serialisation across process boundary |
