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
weekend_scout/regions.py
```
Also check the corresponding test files in `tests/`.
Also check the skill template at `skill_template/weekend-scout.template.md`.

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
- [ ] `format_scout_message` `low_results_hint=True` adds hint in **both** the empty-events path and the normal path
- [ ] `format_scout_message` renders up to 10 trip options (cap is `[:10]`, not `[:3]`)

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
- [ ] **Skill template is the source of truth** — `.claude/skills/weekend-scout/SKILL.md` must be generated, not hand-edited

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
- [ ] `get_region_name` returns `home_city` (not empty string) when city not in regions dict
- [ ] Region lookup uses `regions.py` (`REGIONS` dict) — no `data/regions.json` file read
- [ ] `ensure_geonames()` auto-downloads when file is missing (no `download-data` prerequisite)
- [ ] GeoNames file stored under `<config_dir>/geonames/` via `get_config_dir()` — not inside project `data/`

### 6. Telegram / telegram.py

- [ ] `split_message` never produces a part exceeding `max_length`
- [ ] `send_telegram` validates token **and** chat_id before making any HTTP call
- [ ] HTTP call uses `timeout=` argument (never blocks forever)
- [ ] **HTML** escape applied to user-sourced text via `html.escape()` — not Markdown escape
- [ ] `format_event_block` handles `end_date == start_date` (shows "Sat", not "Sat-Sat")
- [ ] `format_scout_message` omits "ROAD TRIPS:" section when `trip_options` is empty
- [ ] `format_scout_message` signature includes `low_results_hint: bool = False`
- [ ] `low_results_hint=True` appends hint **before** the "Scouted by" footer line
- [ ] Trip rendering uses `trip_options[:10]` — cap is 10, not 3

### 7. Config / config.py

- [ ] `DEFAULT_CONFIG["search_language"]` is `"en"` (not `"pl"`)
- [ ] `DEFAULT_CONFIG["max_trip_options"]` is `10`
- [ ] `DEFAULT_CONFIG["max_searches"]` is `30`
- [ ] `DEFAULT_CONFIG["max_fetches"]` is `30`
- [ ] `load_config` merges stored YAML *over* defaults (not the other way around)
- [ ] `save_config` creates parent directory if it doesn't exist
- [ ] `run_setup_wizard` does not overwrite Telegram token with empty string when user skips
- [ ] `config set` command (in `__main__.py`) validates key exists before saving
- [ ] `config set` coerces value type to match existing (bool, int, float)

### 8. CLI / __main__.py

- [ ] `cmd_init` includes `max_searches` and `max_fetches` in the `config` block of JSON output
- [ ] `format-message` subcommand has `--low-results` argument wired to `format_scout_message(low_results_hint=...)`
- [ ] `--low-results` accepts string `"true"/"false"` (not a boolean flag) — LLM passes it as a string
- [ ] No business logic in `cmd_*` functions — they load config, call module functions, print JSON
- [ ] `cache.py` functions take `config` dict, not a raw path, so tests can inject `_cache_dir`

### 9. Skill template system

- [ ] `skill_template/weekend-scout.template.md` is the source of truth — do not review generated files
- [ ] Generated files exist at `.claude/skills/weekend-scout/SKILL.md`, `.codex/skills/weekend-scout/SKILL.md`, `.openclaw/skills/weekend-scout/SKILL.md`
- [ ] Template Step 1 extracts `max_searches`, `max_fetches`, `tier2`, `tier3` from init output
- [ ] Template Step 2 references `max_searches`/`max_fetches` (not hardcoded 8/10)
- [ ] Template Phase C: per-city individual searches, tier1→tier2→tier3 priority, budget thresholds
- [ ] Template Step 3: trip cap is 10, not 3
- [ ] Template Step 5: `--low-results true` flag shown for `format-message` when `total_events < 3`
- [ ] Template Step 6: low-results hint shown to user when `total_events < 3`
- [ ] Run `python skill_template/generate.py --check` to verify generated files are in sync with template

### 10. Tests

- [ ] Every public function in each module has at least one test
- [ ] Tests use `tmp_path` or `_cache_dir` override — never touch real filesystem or real config
- [ ] No test hardcodes absolute paths
- [ ] Network calls are mocked (no live HTTP in tests)
- [ ] Tests for `send_telegram` mock `requests.post`, not the whole `requests` module
- [ ] `test_parse_geonames_file_skips_pplx` and `test_get_city_list_filters_home_districts` both present
- [ ] `test_split_at_double_newline` and `test_split_at_single_newline_fallback` use messages longer than 4096 chars
- [ ] Test for `max_trip_options` default asserts value is `10` (not `3`)
- [ ] Tests for `format_scout_message` cover the `low_results_hint=True` path
- [ ] Tests for `cmd_init` output verify `max_searches` and `max_fetches` present in config block

### 11. Design / architecture

- [ ] Backlog items in `docs/backlog.md` reflect current implementation state (no TODO items that are actually done)
- [ ] Any deviation from `docs/weekend-scout-mvp-design.md` has an entry in `docs/design_changes.md`
- [ ] `data/` directory does not exist in the repo (regions moved to `regions.py`, geonames to cache dir)

---

## How to run existing tests

Before reporting, run the test suite and the generator check:

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
python skill_template/generate.py --check 2>&1
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
