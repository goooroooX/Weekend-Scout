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
| 2026-03-26 | 4.4 Query Generation | Query keywords are now language-keyed via QUERY_TEMPLATES (pl/de/fr/cs/sk/hu/uk/lt/lv/et/be/en) instead of Polish-only | Design pseudocode showed Polish example only; non-Polish configs need correct local keywords |
| 2026-03-26 | 4.4 Query Generation | `format_date_local` extended to use day-first order for fr/cs/sk/hu/uk/lt/lv/et/be | Manual test revealed these were incorrectly using English "Month Day, Year" order |
| 2026-03-26 | 4.4 Query Generation | English fallback query no longer appends year separately | `en_sat` from `format_date_local` already contains the year; removed duplicate |
| 2026-03-26 | 6. CLI | `main()` reconfigures stdout to UTF-8 on startup | Windows consoles default to cp1251/cp850 which can't encode Polish/Unicode city names in JSON output |
| 2026-03-27 | 5.2 SKILL.md | Full rewrite: explicit `suggested_queries.broad/targeted` usage, log-search pattern shown once for all phases, `format-message` CLI command replaces manual message template, `cache-mark-served` added to Step 6, `searches_this_week` dedup explained, event save schema documented | Multiple gaps between CLI data contract and skill instructions; previous version left targeted queries unused and events were re-sent every week |
| 2026-03-27 | 6. CLI | Added `format-message` subcommand to `__main__.py` exposing `format_scout_message` from telegram.py | `format_event_block` / `format_scout_message` were unreachable from CLI; skill had to replicate formatting manually |
| 2026-03-26 | 4.2 cities.py | `parse_geonames_file` skips rows where `feature_code == "PPLX"` and returns `feature_code`, `admin2`, `admin3` per entry; `get_city_list` skips nearby PPL entries sharing admin codes with the home city | Seven European capitals (Warsaw, Brussels, Madrid, Paris, Dublin, Amsterdam, Stockholm) have city districts incorrectly tagged as plain PPL in GeoNames instead of PPLX, causing them to appear as Tier 1 cities. Two approaches were rejected: (1) `adm4 != ""` filter — unsafe because Germany populates adm4 for all 500 of its PPL entries (standalone cities like Halle, Hamm, Bremerhaven), and France/Belgium similarly; (2) minimum distance threshold — Warsaw's outer districts extend to 14.8 km while real standalone towns start at 9.5 km, creating unavoidable overlap. The implemented solution uses the home city's own `admin2`+`admin3` codes as the discriminator: any PPL entry within 15 km sharing those codes is a district of the home city (districts always share admin codes with their parent). |
