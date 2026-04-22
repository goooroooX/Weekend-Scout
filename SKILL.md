---
name: weekend-scout
description: >
  Discovers next-weekend outdoor events, festivals, and fairs near the user's
  city, builds ranked local picks and road-trip options, and prepares a
  delivery-ready digest through platform-specific agent workflows.
author: Dmitry Nikolaenya
version: 1.0.0
tags:
  - events
  - travel
  - telegram
  - multi-platform
  - python
---
# Weekend Scout

## Overview

Weekend Scout is a multi-platform agent skill plus Python CLI for scouting
outdoor events, festivals, and fairs happening next weekend near the user's
city.

It uses a layered caching system: run-scoped candidate sessions preserve
discovery state while the agent is working, canonicalized events are saved into
a persistent SQLite cache for future weekends and reruns, and deterministic CLI
helpers prepare grouped digest input before delivery.

This repository ships separate runtime `SKILL.md` files for Claude Code,
Codex, and OpenClaw. The repo-root `SKILL.md` exists so directories such as
Skills Directory can index the repository from the root while still pointing
to the canonical platform-specific skill files.

## Instructions

Do not treat this root file as the single canonical runtime prompt for every
platform. Weekend Scout's actual runtime instructions are platform-dependent.

1. Determine which platform is being used.
2. Use this root file only as a platform-neutral repository entry point and
   router.
3. Load the matching generated runtime skill from this repository.
4. Follow that platform file, not this root summary, for the actual scout
   workflow.

### Platform Map

| Platform | Canonical runtime skill |
|----------|-------------------------|
| Claude Code | `.claude/skills/weekend-scout/SKILL.md` |
| Codex | `.agents/skills/weekend-scout/SKILL.md` |
| OpenClaw | `.openclaw/skills/weekend-scout/SKILL.md` |

### Source Of Truth

- Runtime skill generation source: `skill_template/weekend-scout.template.md`
- Generated outputs: `.claude/skills/`, `.agents/skills/`,
  `.openclaw/skills/`, `weekend_scout/skill_data/`
- Product and workflow design: `docs/weekend-scout-design-v2.md`
- Installation and user-facing setup: `README.md`

## Execution Guardrails

- Use the defined `python -m weekend_scout ...` CLI commands as the supported
  interface for config, discovery logging, session reads, cache saves, message
  formatting, and delivery.
- Do not manually edit cache files, transport payloads, YAML config, or SQLite
  data as a substitute for the CLI workflow.
- Treat the generated platform-specific `SKILL.md` plus its bundled references
  as the authoritative runtime contract for command order, payload shape, and
  failure handling.

## Output Format

When this root file is invoked directly, respond with:

- a short explanation that Weekend Scout is multi-platform
- the matching platform-specific `SKILL.md` path for the current environment
- the next file or doc to open if the user is installing or reviewing the
  skill

## Notes

- The root `SKILL.md` is intentionally platform-neutral so the repo can be
  indexed without privileging one platform over another.
- The actual event-scouting behavior lives in the generated platform files and
  their bundled references.
- If the workflow changes, update the template-generated platform skills first
  and keep this root file aligned as a routing and metadata document.
