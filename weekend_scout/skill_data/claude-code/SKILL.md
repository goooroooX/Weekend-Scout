---
name: weekend-scout
description: >
  Scout outdoor events, festivals, and fairs happening next weekend in the
  user's city and nearby cities. Build home-city picks and road-trip options,
  format the digest, and send it to Telegram. Use for actual scout runs and
  reruns of the same workflow. Do not use for codebase maintenance or skill edits.
argument-hint: [city] [radius-km] [--cached-only]
allowed-tools: Bash, Read, Write, WebSearch, WebFetch
disable-model-invocation: true
model: haiku
---

## Weekend Scout

> **Normal run rule:** During a normal scout run, do **not** inspect `weekend_scout` package
> source files to infer schemas, payload shapes, or behavior. Follow this skill plus the bundled
> references as the contract. If the documented contract seems insufficient or inconsistent, stop
> the run and tell the user the skill needs maintenance. Do **not** call `--help` commands during
> a normal run; the CLI shapes are documented here and in the bundled references.
>
> Note: `weekend_scout` is a Python package. `python -m weekend_scout` works from any directory.
> Do **not** prefix commands with `cd <path> &&`. Do not patch behavior ad hoc during execution.
>
> **Reference loading rule:** Do **not** preload all references. Read only the reference needed
> for the current branch and current step. After reading a reference, execute that step before
> opening another reference unless you are blocked. Do **not** open later-stage references during
> Step 1 or Step 2 just because they will be needed later.

### Step 1: Initialize

```bash
python -m weekend_scout init-skill [--city CITY] [--radius KM]
```

- If `needs_setup` is `true`, read `references/onboarding.md` and follow it exactly.
- If `warnings` contains `coordinates_not_set`, read `references/onboarding.md` and follow the
  auto-fix path exactly.
- If either setup condition is true, do **not** open any other reference until setup completes and
  `init-skill` is rerun successfully.
- If neither setup condition is true, do **not** open `references/onboarding.md` during Step 1.
- Do **not** open `references/search-workflow.md` before setup is complete.
- Do **not** open `references/platform-codex.md` before `init-skill`. `init-skill` itself is not a
  file-backed payload call.
- Otherwise extract and keep:

```text
saturday, sunday, home_city
max_city_options, max_trip_options
max_searches, max_fetches
tier1
cities.tier2_count, cities.tier3_count
cached.count, cached.covered_cities, cached.city_counts
run_id
workflow
```

- Treat `workflow` as dynamic run data only:
  - `workflow.audit_command`
  - `workflow.coverage`
  - `workflow.phase_a`
  - `workflow.phase_c`
  - `workflow.phase_d`
- In compact `init-skill`, tier2 and tier3 are not preloaded; request them later on demand.
- Do not recompute localized broad or targeted queries when `workflow.phase_a` or `workflow.phase_c.tier1` already provide them.

### Step 2: Search

- Before discovery work, read `references/search-workflow.md`.
- Do **not** open scoring or delivery references during Step 2.
- If the user invoked `/weekend-scout --cached-only`, follow the cached-only path from that reference.
- Otherwise follow the full Step 2 contract from that reference exactly.

### Step 3: Score And Step 4: Build Trips

- Before scoring or trip building, read `references/scoring-and-trips.md`.
- Do **not** open the delivery reference until Step 5.
- Follow that reference exactly for the score rubric, selection caps, trip construction, and `score_summary`.

### Step 5: Format/Send And Step 6: Mark Served/Report

- Before formatting or sending, read `references/delivery-and-audit.md`.
- Follow that reference exactly for `format-message`, `send`, `run_complete`, `audit-run`, and the final user report.
- Use `workflow.audit_command` as the run-scoped audit command for this execution.
