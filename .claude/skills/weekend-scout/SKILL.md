---
name: weekend-scout
description: >
  Scout outdoor events, festivals, and fairs happening next weekend
  in your city and nearby cities. Builds trip options and posts to Telegram.
argument-hint: [city] [radius-km] [--cached-only]
allowed-tools: Bash, Read, Write, WebSearch, WebFetch
disable-model-invocation: true
model: haiku
---

## Weekend Scout

> Note: `weekend_scout` is a Python package — `python -m weekend_scout` works from any
> directory. Do **not** prefix commands with `cd <path> &&`.


### Step 1: Initialize

```bash
python -m weekend_scout init [--city CITY] [--radius KM]
```

**Check for setup issues before extracting variables:**

- If `"needs_setup": true` → city not configured; run the **full setup flow** below.
- If `output.warnings` contains `"coordinates_not_set"` → city set but coords missing;
  run the **auto-fix flow** below.
- Otherwise → proceed directly to variable extraction.

---

**Full setup flow** (`needs_setup: true` — no city configured):

Ask the user:

> "Weekend Scout needs a quick one-time setup.
> What city do you live in? (Include the country if the name is common across countries,
> e.g. 'Lyon, France'.) How far are you willing to drive for a day trip? (default: 150 km)"

Wait for the reply. Parse: `setup_city`, optional `setup_country`, `setup_radius` (default 150).

**Auto-fix flow** (`coordinates_not_set` — city known, coords missing):

Set `setup_city = output.config.home_city`, `setup_country = output.config.home_country`,
`setup_radius = output.config.radius_km`. No user question needed — tell the user:
*"Resolving coordinates for `<setup_city>`..."*

---

**Resolve coordinates** (used by both flows above):

```bash
python -m weekend_scout find-city --name "<setup_city>" [--country "<setup_country>"]
```

- **No matches** or `"warning"` in output: WebSearch
  `"<setup_city> city coordinates latitude longitude"` → extract lat, lon, country.
- **Exactly 1 match**: use it.
- **Multiple matches** (different countries): list them and ask the user which country;
  use the chosen result.

Once resolved:
```bash
python -m weekend_scout setup --json '{"home_city":"<name>","home_country":"<country>","home_coordinates":{"lat":<lat>,"lon":<lon>},"radius_km":<radius>,"search_language":"<lang>"}'
```

Tell the user: *"Configured — scouting near <city>, <country>."*
Then re-run `python -m weekend_scout init` and continue from variable extraction below.

---

The `init` JSON contains all config fields you need — do **not** run `config` separately.

Extract these fields from the JSON output and keep them in mind throughout:

```
saturday     = output.config.target_weekend.saturday   (ISO date)
sunday       = output.config.target_weekend.sunday     (ISO date)
home_city    = output.config.home_city                 (departure/arrival label for trip routes)
max_searches = output.config.max_searches              (search budget limit)
max_fetches  = output.config.max_fetches               (fetch budget limit)
tier1        = output.cities.tier1                     (largest nearby cities, highest population)
tier2        = output.cities.tier2                     (medium-population nearby cities)
tier3        = output.cities.tier3                     (smallest nearby cities)
cached       = output.cached_events                    (already in cache — skip re-discovering)
done_q       = output.searches_this_week               (queries already run this week — skip)
run_id       = output.run_id                           (pass to all log-search and log-action calls)
qvars        = output.suggested_queries.vars           (substitution variables for templates)
broad_q      = output.suggested_queries.broad          (4 templates — fill {placeholders} from qvars)
tgt_tmpl     = output.suggested_queries.targeted_template  ({city} and {date} are placeholders)
```

### Step 2: Search for Events

**If invoked with `--cached-only`**: skip this entire step. Proceed directly to Step 3
using only the `cached` events from Step 1.

**Offline pre-check (no tool calls):** Review `cached`. If it already has events for
every city in `tier1` for the target weekend, skip directly to Step 3.

**Budget: up to `max_searches` WebSearch calls + up to `max_fetches` WebFetch calls.**
Bash CLI calls (`save`, `log-search`, etc.) are free — they do not count.

Track usage mentally throughout this step:
- `searches_used` — increment by 1 after every WebSearch
- `fetches_used`  — increment by 1 after every WebFetch
- Before any WebSearch: stop if `searches_used >= max_searches`
- Before any WebFetch:  stop if `fetches_used  >= max_fetches`

**Budget allocation guidance:**
```
Phase A  (broad)        : up to 5 searches + up to 6 fetches
Phase B  (aggregators)  : counts against the 6 fetch slots above
Phase C  (per-city)     : up to 2 searches + 1 fetch per uncovered tier1 city
                          up to 1 search per uncovered tier2 city (if searches_used < max_searches × 0.6)
                          up to 1 search per uncovered tier3 city (if searches_used < max_searches × 0.8)
Phase D  (verification) : up to 5 fetches (reserve capacity before Phase C)
```

**Log pattern** — call after every search or aggregator fetch:
```bash
python -m weekend_scout log-search \
  --query "<query_or_url>" --target-weekend "<saturday>" \
  --cities '["<city>"]' \
  --phase <broad|aggregator|targeted|verification> \
  --result-count <N> \
  --events-discovered <N> \
  --run-id "<run_id>"
```
`<N>` in `--events-discovered` is an **integer count** (e.g. `3`), not a list. Use `0` if no events were identified in this search.

**Event schema** — required fields for `save` (optional fields improve scoring):
```
Required: event_name (str), city (str), start_date (YYYY-MM-DD)
Scoring:  confidence ("confirmed"|"likely"|"unverified"), category (str),
          free_entry (bool), source_url (str), source_name (str)
Optional: end_date, time_info, location_name, lat, lon, description, country
```

---

**Phase A — Broad sweep (3–5 searches):**
Check: if ALL broad_q queries are already in `done_q`, log `skip` and move on:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase A --target-weekend "<saturday>" --detail '{"reason": "all_queries_in_done_q"}'
```
Otherwise log `phase_start` and run:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start --phase A --target-weekend "<saturday>"
```
For each template in `broad_q`: fill it → `query = template.format(**qvars)`.
Skip if `query` is already in `done_q`. Run WebSearch(query).

After each search, examine results:
- Specific event title (name + city + date) → record it immediately
- Aggregator URL listing many events → queue for Phase B
- Irrelevant (museums, indoor, wrong dates) → skip

Log each search with `--phase broad`.

**Phase B — Aggregator deep-dive (3–8 fetches):**
Check: if no aggregator URLs were queued in Phase A, log `skip` and move on:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase B --target-weekend "<saturday>" --detail '{"reason": "no_aggregator_urls"}'
```
Otherwise log `phase_start` and run:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start --phase B --target-weekend "<saturday>"
```
Fetch the most promising aggregator URLs. Use this prompt:

> "List ALL outdoor events, festivals, fairs, markets, city days, reenactments, food
> festivals, and street events happening on [DATES] within the area covered by this page.
> For each: event name, city, venue, dates/times, 1-sentence description, free entry or not.
> Exclude: museums, galleries, theaters, cinemas, indoor events, weekly markets."

Log each fetch with `--phase aggregator`.

**Phase C — Targeted city searches:**
Log `phase_start`:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start --phase C --target-weekend "<saturday>"
```

Search cities in priority order: **tier1 first** (largest population), then tier2, then tier3.
Stop when budget is exhausted.

**Rules:**
- **Always search each uncovered city individually** — never combine multiple cities in one query.
- Each uncovered **tier1** city: run up to 2 WebSearch calls (first broad, then specific if the
  first returns nothing useful). Optionally fetch the most promising URL found (1 WebFetch).
- Each uncovered **tier2** city: 1 WebSearch — only if `searches_used < max_searches × 0.6`.
- Each uncovered **tier3** city: 1 WebSearch — only if `searches_used < max_searches × 0.8`.
- A city is "covered" if it has at least one event across `cached` + Phase A+B+C results.
- If all cities in all tiers are already covered, log skip:
  ```bash
  python -m weekend_scout log-action --run-id "<run_id>" --action skip \
    --phase C --target-weekend "<saturday>" --detail '{"reason": "all_cities_covered"}'
  ```

For each targeted search:
fill → `query = tgt_tmpl.format(city=city_name, date=qvars["date"])`.
Skip if `query` is in `done_q`. Run WebSearch(query).
Log each with `--phase targeted`.

**Phase D — Verification (1–5 fetches):**
Check: if all top candidates already have `confidence: "confirmed"`, log `skip` and move on:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase D --target-weekend "<saturday>" --detail '{"reason": "all_confirmed"}'
```
Otherwise log `phase_start` and run:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start --phase D --target-weekend "<saturday>"
```
For your top 5 candidate events, fetch the official source to confirm dates and details.
Update `confidence` to `"confirmed"`. Log with `--phase verification`.

---

Save ALL discovered events (including future-weekend finds):
```bash
python -m weekend_scout save --run-id "<run_id>" --events '<JSON array>'
```

### Step 3: Score and Rank

Score each event 1–10:
- Category match (festival/fair = high, generic = low): 0–3
- Scale (city-wide = high, small local = low): 0–2  *(infer from description)*
- Uniqueness (annual = high, recurring = low): 0–2  *(infer from description)*
- Confidence (confirmed=1, likely=0.5, unverified=0): 0–1
- Free entry: 0–1
- Source quality (official=1, aggregator=0.5): 0–1

Pool: combine `cached` events + newly saved events.
Select: top 3 in home city + up to 10 road trip options from nearby cities (tier1 first, then tier2, tier3).

After selecting, compute: `total_events = len(city_events_selected) + len(trip_options)`

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action score_summary \
  --target-weekend "<saturday>" \
  --detail '{"total_pool": <N>, "city_events_selected": <N>, "trip_options": <N>}'
```

### Step 4: Build Trip Options

For road trips, use tier as a distance proxy (tier1 = largest/closest, tier3 = smallest/farthest):
Build up to 10 options — one per city that has confirmed events, working through tier1 → tier2 → tier3.
Label them A through J.

For each trip option, build a dict for `format-message`:
```json
{
  "name":   "Łódź Day Trip",
  "route":  "Warsaw → Łódź (130 km, ~1h45) → Warsaw",
  "events": "Festiwal Czterech Kultur | ul. Piotrkowska | Sat–Sun all day",
  "timing": "Leave by: 10:00 | Back by: ~20:00",
  "url":    "https://example.com/event"
}
```

Use `home_city` as the start/end point name in the route.

**"Leave by"** timing = the latest you can depart and still arrive when the event is **in
full swing** (not at opening). Formula: `event_start + 1h30 − drive_time`.
Minimum departure: **09:00** (never suggest leaving before 09:00).
Example: event opens at 10:00, drive 1h30 → peak at 11:30 → leave by **10:00** (not 08:30).
If the event has no known start time, use **09:30** as default departure.
`url` is optional — include it when you have an official event URL (renders as `[link]` in the message).

### Step 5: Format and Send

```bash
python -m weekend_scout format-message \
  --saturday "<saturday>" --sunday "<sunday>" \
  --city-events '<top_3_city_events_json>' \
  --trips '<trip_options_json>' \
  [--low-results true]   # include this flag when total_events < 3
# → {"written": "<path>"}  — use this path for send:

python -m weekend_scout send --file "<path from written>"
```

**Always display the message to the user** — read the written file and show its contents
in the conversation (strip HTML tags when presenting; the content reads fine as plain text).

If `{"sent": true}`: tell the user the digest was sent to Telegram.

If `{"sent": false}`:
- **Telegram not configured** (`telegram_bot_token` or `telegram_chat_id` blank in config):
  Tell the user:

  > Telegram is not configured. To set it up, run:
  > ```
  > python -m weekend_scout config telegram_bot_token YOUR_BOT_TOKEN
  > python -m weekend_scout config telegram_chat_id YOUR_CHAT_ID
  > ```
  > Then run `/weekend-scout` again to send this weekend's digest.

- **Telegram configured but send failed**: report the error and suggest verifying
  the token and chat ID with `python -m weekend_scout config`.

### Step 6: Mark Served and Report

```bash
# Only if send succeeded ({"sent": true}):
python -m weekend_scout cache-mark-served --date "<saturday>"

python -m weekend_scout log-action --run-id "<run_id>" --action run_complete \
  --target-weekend "<saturday>" \
  --detail '{"events_sent": <city_count + trip_count>, "new_events": <N>, "budget_used": "<searches_used>/<max_searches> searches + <fetches_used>/<max_fetches> fetches"}'
```

Tell the user:
- How many events were found / how many are new vs cached
- Budget used: `searches_used`/`max_searches` searches, `fetches_used`/`max_fetches` fetches
- Any cities with zero coverage (tier1 most important — flag for next run)

**If `total_events < 3`**, also tell the user:
> Only N event(s) found. To discover more, increase your search budget:
> ```
> python -m weekend_scout config max_searches 50
> python -m weekend_scout config max_fetches 50
> ```

---

### Event filter (reference)

**Include:** open-air festivals (music, food, craft, cultural), City Days, large fairs and
markets, historical reenactments, street art festivals, food truck rallies, beer/wine festivals,
outdoor concerts, open-air cinema, large sporting events with public attendance.

**Exclude:** museum openings, indoor theater/cinema/opera, conferences, small recurring weekly
farmers markets, private corporate events, ticketed indoor concerts.
Religious services are excluded, but religious festivals and processions are included.
