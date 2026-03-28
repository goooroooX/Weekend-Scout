# Weekend Scout -- Project Guide

## What this is
A multi-platform Agent Skill + Python CLI that discovers weekend outdoor events near the
user's city and sends curated trip options to Telegram.

## Key documents
- **Design:** docs/weekend-scout-mvp-design.md (the source of truth for architecture)
- **Backlog:** docs/backlog.md (track all features, update status when implementing)
- **Design changes:** docs/design_changes.md (log ANY deviation from the design doc)
- **Platform reference:** docs/platform-skill-reference.md

## Development rules

### Backlog tracking (MANDATORY)
When you start working on any feature or task:
1. Check docs/backlog.md for the relevant item
2. Change its status to `IN PROGRESS`
3. When done, change to `DONE` and add completion date
4. If you discover new tasks during implementation, add them to the backlog

### Design change tracking (MANDATORY)
When implementation differs from docs/weekend-scout-mvp-design.md:
1. Add an entry to docs/design_changes.md with date, section, what changed, and why
2. Keep entries concise but specific

### Code standards
- Python 3.10+ with type hints on all public functions
- Cross-platform: use pathlib.Path everywhere, never hardcode Unix or Windows paths
- Config directory: use platformdirs library for cross-platform config path
  (~/.config/weekend-scout on Linux/Mac, AppData\Local\weekend-scout on Windows)
- GeoNames data: downloaded automatically to `<config_dir>/geonames/cities15000.txt`
  (not the project data/ directory, which no longer exists)
- Region mapping: `weekend_scout/regions.py` Python module (not data/regions.json)
- Minimal dependencies: only pyyaml, requests, platformdirs
- All CLI commands should work standalone for testing
- Use argparse for CLI, with subcommands: setup, config, init, save, send,
  cache-query, log-search, cache-mark-served, run
- SQLite via built-in sqlite3 module
- Print JSON output from CLI commands so the skill can parse it
- Tests use pytest, no external test dependencies beyond pytest itself

### Skill development
- **Source of truth:** `skill_template/weekend-scout.template.md`
- After editing the template, regenerate with: `python skill_template/generate.py`
- Generated skill files live in:
  - `.claude/skills/weekend-scout/SKILL.md` (Claude Code)
  - `.codex/skills/weekend-scout/SKILL.md` (Codex)
  - `.openclaw/skills/weekend-scout/SKILL.md` (OpenClaw)
- Do NOT edit the generated SKILL.md files directly — edit the template
- Claude Code skill uses `disable-model-invocation: true` (user-triggered only via /weekend-scout)
- The skill orchestrates: it calls Python CLI for data, runs WebSearch/WebFetch
  for event discovery, then calls Python CLI for output
- Test the skill by running /weekend-scout in Claude Code after generating

### Testing approach
- Each Python module should be testable independently
- Tests should not require network access or API keys
- Use fixtures for SQLite (in-memory DB) and config (temp directory)
- Run tests: python -m pytest tests/ -v

### Git conventions
- Commit after each backlog item is completed
- Commit message format: "[COMPONENT] Brief description"
  Examples: "[config] Add setup wizard", "[cache] Implement SQLite schema"
