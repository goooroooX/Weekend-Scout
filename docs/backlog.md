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
| 1.2 | Implement config.py: default config generation | TODO | |
| 1.3 | Implement config.py: setup wizard (interactive prompts) | TODO | |
| 1.4 | Implement config.py: read/write YAML config | TODO | |
| 1.5 | Implement config.py: config path resolution (cross-platform) | TODO | |
| 1.6 | Implement __main__.py: CLI entry point with argparse subcommands | TODO | |
| 1.7 | Write tests for config.py | TODO | |

## Phase 2: City List + Distance

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Download and integrate GeoNames cities15000.txt | TODO | |
| 2.2 | Implement cities.py: parse GeoNames file | TODO | |
| 2.3 | Implement distance.py: Haversine formula | TODO | |
| 2.4 | Implement distance.py: driving time heuristic | TODO | |
| 2.5 | Implement cities.py: filter by radius + assign tiers | TODO | |
| 2.6 | Implement cities.py: generate search queries (broad + targeted) | TODO | |
| 2.7 | Create data/regions.json for Poland | TODO | |
| 2.8 | Implement cities.py: city list caching (JSON file) | TODO | |
| 2.9 | Wire "init" CLI command (returns config + cities + queries) | TODO | |
| 2.10 | Write tests for cities.py and distance.py | TODO | |

## Phase 3: Event Cache

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | Implement cache.py: SQLite schema creation | TODO | |
| 3.2 | Implement cache.py: save events (with dedup) | TODO | |
| 3.3 | Implement cache.py: query events by date range | TODO | |
| 3.4 | Implement cache.py: log searches | TODO | |
| 3.5 | Implement cache.py: mark events as served | TODO | |
| 3.6 | Implement cache.py: cleanup old events (30+ days) | TODO | |
| 3.7 | Wire cache CLI commands (save, cache-query, log-search, cache-mark-served) | TODO | |
| 3.8 | Write tests for cache.py | TODO | |

## Phase 4: Telegram Sender

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Implement telegram.py: format message (Markdown) | TODO | |
| 4.2 | Implement telegram.py: send via Bot API (requests) | TODO | |
| 4.3 | Implement telegram.py: message splitting (>4096 chars) | TODO | |
| 4.4 | Wire "send" CLI command | TODO | |
| 4.5 | Write tests for telegram.py (mock HTTP) | TODO | |

## Phase 5: Claude Code Skill

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Write SKILL.md with full search strategy prompt | TODO | |
| 5.2 | Test /weekend-scout with real web searches | TODO | |
| 5.3 | Iterate on search queries based on result quality | TODO | |
| 5.4 | Iterate on scoring rubric | TODO | |
| 5.5 | End-to-end test: init -> search -> save -> send | TODO | |

## Phase 6: Polish

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6.1 | Add region mappings beyond Mazowsze | TODO | |
| 6.2 | Handle "no events found" gracefully | TODO | |
| 6.3 | Add cron/scheduled execution instructions to README | TODO | |
| 6.4 | Cross-platform testing (Windows native, WSL) | TODO | |
