# Weekend Scout -- Backlog

## Status legend
- `TODO` -- not started
- `IN PROGRESS` -- currently being worked on
- `DONE (YYYY-MM-DD)` -- completed
- `BLOCKED` -- waiting on something
- `DEFERRED` -- moved out of MVP scope

---

## Phase 1: Project Skeleton + Config

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Create project structure (pyproject.toml, dirs, __init__ files) | DONE (2026-03-26) | |
| 1.2 | Implement config.py: default config generation | DONE (2026-03-26) | |
| 1.3 | Implement config.py: setup wizard (interactive prompts) | DONE (2026-03-26) | |
| 1.4 | Implement config.py: read/write YAML config | DONE (2026-03-26) | |
| 1.5 | Implement config.py: config path resolution (cross-platform) | DONE (2026-03-26) | |
| 1.6 | Implement __main__.py: CLI entry point with argparse subcommands | DONE (2026-03-26) | Done during scaffolding |
| 1.7 | Write tests for config.py | DONE (2026-03-26) | |

## Phase 2: City List + Distance

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Add `download-data` CLI command: fetch + unzip cities15000.zip from GeoNames | DONE (2026-03-26) | |
| 2.2 | Implement cities.py: parse GeoNames file | DONE (2026-03-26) | |
| 2.3 | Implement distance.py: Haversine formula | DONE (2026-03-26) | Done during scaffolding |
| 2.4 | Implement distance.py: driving time heuristic | DONE (2026-03-26) | Done during scaffolding |
| 2.5 | Implement cities.py: filter by radius + assign tiers | DONE (2026-03-26) | |
| 2.6 | Implement cities.py: generate search queries (broad + targeted) | DONE (2026-03-27) | Redesigned to return templates+vars; `--city` override now geocodes coordinates/language |
| 2.7 | Create data/regions.json for Poland | DONE (2026-03-26) | Done during scaffolding |
| 2.8 | Implement cities.py: city list caching (JSON file) | DONE (2026-03-26) | |
| 2.9 | Wire "init" CLI command (returns config + cities + queries) | DONE (2026-03-26) | Wired during scaffolding; fully functional after Phase 3 |
| 2.10 | Write tests for cities.py and distance.py | DONE (2026-03-26) | |

## Phase 3: Event Cache

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | Implement cache.py: SQLite schema creation | DONE (2026-03-26) | |
| 3.2 | Implement cache.py: save events (with dedup) | DONE (2026-03-26) | |
| 3.3 | Implement cache.py: query events by date range | DONE (2026-03-26) | |
| 3.4 | Implement cache.py: log searches | DONE (2026-03-26) | |
| 3.5 | Implement cache.py: mark events as served | DONE (2026-03-26) | |
| 3.6 | Implement cache.py: cleanup old events (30+ days) | DONE (2026-03-26) | |
| 3.7 | Wire cache CLI commands (save, cache-query, log-search, cache-mark-served) | DONE (2026-03-26) | Wired during scaffolding |
| 3.8 | Write tests for cache.py | DONE (2026-03-26) | |

## Phase 4: Telegram Sender

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Implement telegram.py: format message (Markdown) | DONE (2026-03-26) | |
| 4.2 | Implement telegram.py: send via Bot API (requests) | DONE (2026-03-26) | |
| 4.3 | Implement telegram.py: message splitting (>4096 chars) | DONE (2026-03-26) | |
| 4.4 | Wire "send" CLI command | DONE (2026-03-26) | Wired during scaffolding |
| 4.5 | Write tests for telegram.py (mock HTTP) | DONE (2026-03-26) | |

## Phase 5: Claude Code Skill

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Write SKILL.md with full search strategy prompt | DONE (2026-03-27) | Implemented in .claude/skills/weekend-scout/SKILL.md (177 lines, 6 steps) |
| 5.2 | Test /weekend-scout with real web searches | IN PROGRESS | Clean-run test done 2026-03-27: Phase A completed (4 searches, 0 events), interrupted before Phase B; exposed bugs fixed in 5.6 |
| 5.3 | Iterate on search queries based on result quality | TODO | |
| 5.4 | Iterate on scoring rubric | TODO | |
| 5.5 | End-to-end test: init -> search -> save -> send | TODO | |

## Phase 6: Polish

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6.1 | Add region mappings beyond Mazowsze | DONE (2026-03-27) | data/regions.json expanded to ~80 EU cities (Berlin, Paris, Vienna, Budapest, Brussels, etc.) |
| 6.2 | Handle "no events found" gracefully | DONE (2026-03-27) | format_scout_message returns "No events found" message when both city_events and trip_options are empty |
| 6.3 | Add cron/scheduled execution instructions to README | TODO | |
| 6.4 | Cross-platform testing (Windows native, WSL) | TODO | |

## Phase 7: Post-Launch Tuning

| # | Task | Status | Notes |
|---|------|--------|-------|
| 7.1 | Switch Telegram formatting to native HTML | DONE (2026-03-27) | parse_mode="HTML"; html.escape() for all user text; bold/italic/links via <b>/<i>/<a> |
| 7.2 | Unified JSONL action logging | DONE (2026-03-27) | log_action() in cache.py + log-action CLI; all phases/lifecycle events logged to action_log.jsonl with run_id |
| 7.3 | Cache-only mode for skill (--cached-only) | DONE (2026-03-27) | SKILL.md skips Step 2 when flag set |
| 7.4 | Pin skill to Haiku model | DONE (2026-03-27) | model: haiku frontmatter in SKILL.md |
| 7.5 | Inline [link] on description/venue line | DONE (2026-03-27) | Removed separate source footer; link appended to desc line (or venue if no desc); trip url field added |
| 7.6 | Fix "Leave by:" departure timing rule | DONE (2026-03-27) | Formula: event_start + 1h30 − drive_time, min 09:00; documented in SKILL.md Step 4 |
| 7.7 | Logging enhancements (events_discovered, skip actions, run_complete) | DONE (2026-03-27) | --events-discovered on log-search; --run-id on save; skip vs phase_start logic; run_complete in Step 6 |
| 7.8 | Expand language/country support to 27 countries | DONE (2026-03-27) | Added IT/ES/PT/NL/SE/NO/DK/FI/RO/HR/BG/RS/GR/TR/RU with month names and query templates |
| 7.9 | Fix first-run onboarding: needs_setup guard in init + SKILL.md gate | DONE (2026-03-27) | init returns needs_setup:true when home_city blank; SKILL.md shows setup msg and stops |
| 7.10 | Fix --events-discovered CLI type error (int vs list) | DONE (2026-03-27) | SKILL.md log pattern clarified: integer count, not a list |

## Phase 8: Onboarding & UX

| # | Task | Status | Notes |
|---|------|--------|-------|
| 8.1 | Redesign setup wizard: city-only input, auto-geocode from GeoNames | DONE (2026-03-27) | run_setup_wizard asks only city + radius; auto-fills coords/country/lang; multi-country disambiguation; testable via _geonames_path param |
| 8.2 | Add find-city CLI command | DONE (2026-03-27) | python -m weekend_scout find-city --name X [--country Y]; returns JSON matches from GeoNames; no-file warning |
| 8.3 | Add setup --json flag for skill-driven config | DONE (2026-03-27) | python -m weekend_scout setup --json '{...}'; merges into config, invalidates stale city cache |
| 8.4 | Fix DEFAULT_CONFIG: remove hardcoded Poland/Warsaw defaults | DONE (2026-03-27) | home_country:"", home_coordinates:{lat:0.0,lon:0.0}; 0,0 is the unset sentinel |
| 8.5 | SKILL.md: full in-chat onboarding flow (find-city + WebSearch fallback + setup --json) | DONE (2026-03-27) | Handles needs_setup + coordinates_not_set; no manual terminal setup needed |
| 8.6 | SKILL.md: always display message to user; improved Telegram unconfigured guidance | DONE (2026-03-27) | Message shown in chat; config commands suggested when Telegram not set |
