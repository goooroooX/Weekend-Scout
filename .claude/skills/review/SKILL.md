---
name: review
description: >
  Code review for Weekend Scout. Reads source files and reports bugs,
  violations of project standards, and improvement opportunities.
argument-hint: [file-or-directory]
allowed-tools: Read, Glob, Grep, Bash
disable-model-invocation: true
---

## Weekend Scout — Code Review

You are doing a focused code review of the Weekend Scout project.
Read the target files, apply every check below, and report findings.

### What to review

If the user provided an argument, review that file or directory.
If no argument, review the full Python package:
```
weekend_scout/__main__.py
weekend_scout/config.py
weekend_scout/cities.py
weekend_scout/distance.py
weekend_scout/cache.py
weekend_scout/telegram.py
```
Also check the corresponding test files in `tests/`.

Read each file fully before making any judgement.

---

## Checklist

Work through every section. Report every finding — do not stop at the first issue per file.

### 1. Correctness — bugs and wrong behaviour

- [ ] Functions return the correct type in all code paths (including early returns)
- [ ] `None` / missing dict keys handled at every `.get()` call that feeds into downstream logic
- [ ] Integer/float conversions wrapped in `try/except` where user or external data is the source
- [ ] SQLite queries use parameterised bindings — no f-strings or `.format()` in SQL
- [ ] `INSERT OR IGNORE` dedup relies on UNIQUE constraint — verify constraint exists in schema
- [ ] `split_message` never returns an empty list; always at least `[""]`
- [ ] `send_telegram` returns `False` (not raises) on network error
- [ ] `next_weekend_dates` skips the *current* Saturday if today is Saturday (not just "days_ahead=7")
- [ ] `parse_geonames_file` PPLX filter and admin-code district filter both applied correctly
- [ ] Cache `query_events` covers both Saturday **and** Sunday of the target weekend
- [ ] `format_event_block` doesn't crash when `free_entry` is `0` (falsy but not None)

### 2. Project standards (from CLAUDE.md)

- [ ] **Type hints** on every public function signature (`def foo(x: str) -> list[str]:`)
- [ ] **pathlib.Path** used for all file paths — no `os.path`, no string concatenation of paths
- [ ] **No hardcoded Unix/Windows paths** — no `/tmp/`, no `C:\`, no `~`
- [ ] **platformdirs** used for config/cache directory (not manual `~/.config` construction)
- [ ] **No hardcoded `"pl"`** language default — fallback must be `"en"`
- [ ] **No hardcoded `"PL"`** country code — default must be `""`
- [ ] **Minimal dependencies** — no imports beyond pyyaml, requests, platformdirs, sqlite3, stdlib
- [ ] **CLI commands print JSON** — every `cmd_*` function outputs parseable JSON, not plain text
- [ ] **No `os.path`** usage anywhere

### 3. Cross-platform safety

- [ ] No `os.sep` or `\\` path separators hardcoded
- [ ] File opens use `encoding="utf-8"` explicitly
- [ ] `sys.stdout.reconfigure(encoding="utf-8")` present in `main()` for Windows console safety
- [ ] No shell=True in any Bash/subprocess call
- [ ] Temp file paths (if any) use `tempfile` or `pathlib.Path` — not hardcoded `/tmp/`

### 4. SQLite / cache.py

- [ ] `CREATE TABLE IF NOT EXISTS` used — safe to call on existing DB
- [ ] `conn.row_factory = sqlite3.Row` set before queries
- [ ] All connections closed or used as context managers
- [ ] `dedup_key` function produces consistent output (same inputs → same key)
- [ ] `cleanup_old_events` uses correct date comparison (ISO strings compare correctly as text)
- [ ] No raw SQL string formatting with user data

### 5. GeoNames / cities.py

- [ ] `parse_geonames_file` skips rows with `len(cols) < 19` before indexing
- [ ] PPLX filter applied before appending to list
- [ ] Home-city admin-code filter targets only `feature_code == "PPL"` (not PPLA*)
- [ ] `get_city_list` uses cache when available and writes cache when not
- [ ] Cache file name encodes both `home_city` and `radius_km` (cache key is correct)
- [ ] `generate_broad_queries` language fallback is `"en"`, not `"pl"`
- [ ] `get_region_name` returns `home_city` (not empty string) when city not in regions.json

### 6. Telegram / telegram.py

- [ ] `split_message` never produces a part exceeding `max_length`
- [ ] `send_telegram` validates token **and** chat_id before making any HTTP call
- [ ] HTTP call uses `timeout=` argument (never blocks forever)
- [ ] Markdown escape applied to user-sourced text (event names, descriptions) before sending
- [ ] `format_event_block` handles `end_date == start_date` (shows "Sat", not "Sat-Sat")
- [ ] `format_scout_message` omits "ROAD TRIPS:" section when `trip_options` is empty

### 7. Config / config.py

- [ ] `DEFAULT_CONFIG["search_language"]` is `"en"` (not `"pl"`)
- [ ] `load_config` merges stored YAML *over* defaults (not the other way around)
- [ ] `save_config` creates parent directory if it doesn't exist
- [ ] `run_setup_wizard` does not overwrite Telegram token with empty string when user skips
- [ ] `config set` command (in `__main__.py`) validates key exists before saving
- [ ] `config set` coerces value type to match existing (bool, int, float)

### 8. Tests

- [ ] Every public function in each module has at least one test
- [ ] Tests use `tmp_path` or `_cache_dir` override — never touch real filesystem or real config
- [ ] No test hardcodes absolute paths
- [ ] Network calls are mocked (no live HTTP in tests)
- [ ] Tests for `send_telegram` mock `requests.post`, not the whole `requests` module
- [ ] `test_parse_geonames_file_skips_pplx` and `test_get_city_list_filters_home_districts` both present
- [ ] `test_split_at_double_newline` and `test_split_at_single_newline_fallback` use messages longer than 4096 chars

### 9. Design / architecture

- [ ] No business logic in `__main__.py` — cmd functions only load config, call module functions, print JSON
- [ ] `cache.py` functions take `config` dict, not a raw path, so tests can inject `_cache_dir`
- [ ] Backlog items in `docs/backlog.md` reflect current implementation state
- [ ] Any deviation from `docs/weekend-scout-mvp-design.md` has an entry in `docs/design_changes.md`

---

## How to run existing tests

Before reporting, run the test suite to see if there are already failing tests:

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Report any failures as **P0 — test failure** findings.

---

## Report format

Group findings by severity. Within each group, sort by file.

```
## P0 — Bugs / test failures
[file:line] Short description of the problem.
  Why it matters: ...
  Fix: ...

## P1 — Standard violations (CLAUDE.md rules broken)
[file:line] ...

## P2 — Robustness / edge cases
[file:line] ...

## P3 — Minor / style
[file:line] ...

## ✓ Passed checks (summary)
List the checklist sections that passed with no findings.
```

If a file or section is clean, say so explicitly — don't leave the user guessing.
Finish with a one-line overall verdict: **Clean**, **Minor issues**, or **Needs attention**.
