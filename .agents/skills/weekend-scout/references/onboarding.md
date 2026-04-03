# Onboarding And Auto-Fix

Use this reference only when `init-skill` returns `needs_setup: true` or a
`coordinates_not_set` warning.

Do **not** inspect package source or call `--help` during a normal run. The
commands below are the contract.

## 1. Full setup flow (`needs_setup: true`)

Ask the user:

> "Weekend Scout needs a quick one-time setup. What city do you live in, and How far (in km) are you willing to drive for a day trip? (example: Warsaw, 100)"

Wait for the reply. Parse:

- `setup_city`
- optional `setup_country`
- `setup_radius` (default `150`)

Then continue to coordinate resolution.

## 2. Auto-fix flow (`coordinates_not_set`)

Set:

- `setup_city = output.config.home_city`
- `setup_country = output.config.home_country`
- `setup_radius = output.config.radius_km`

Tell the user:

> "Resolving coordinates for `<setup_city>`..."

Then continue to coordinate resolution.

## 3. Resolve coordinates

Run:

```bash
python -m weekend_scout find-city --name "<setup_city>" [--country "<setup_country>"]
```

Handle the result exactly:

- No matches or a warning in output: use `WebSearch("<setup_city> city coordinates latitude longitude")`, then extract
  `lat`, `lon`, and `country`.
- Exactly one match: use it.
- Multiple matches from different countries: show the choices to the user and ask which country to use.

Once resolved:

- Use the resolved match language for `search_language`.
- Build the setup payload with:
  - `home_city`
  - `home_country`
  - `home_coordinates.lat`
  - `home_coordinates.lon`
  - `radius_km`
  - `search_language`

Before writing the setup payload, read `references/platform-codex.md`.
Write the setup JSON object to `setup_json_path`, then run:

Persist with:

```bash
python -m weekend_scout setup --json-file "$setup_json_path"
```

Tell the user:

> "Configured -- scouting near <city>, <country>."

Then rerun:

```bash
python -m weekend_scout init-skill
```

Continue only after the rerun returns normal runtime data.
