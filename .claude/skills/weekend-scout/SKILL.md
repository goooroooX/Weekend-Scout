---
name: weekend-scout
description: >
  Scout outdoor events, festivals, and fairs happening next weekend
  in your city and nearby cities. Builds trip options and posts to Telegram.
argument-hint: [city] [radius-km] [--cached-only]
allowed-tools: Bash, Read, Write, WebSearch, WebFetch
disable-model-invocation: true
---

## Weekend Scout

> Note: `weekend_scout` is a Python package — `python -m weekend_scout` works from any
> directory. Do **not** prefix commands with `cd <path> &&`.

### Step 1: Initialize

```bash
python -m weekend_scout init [--city CITY] [--radius KM]
```

First run: `python -m weekend_scout setup` then re-run init.

Extract these fields from the JSON output and keep them in mind throughout:

```
saturday  = output.config.target_weekend.saturday   (ISO date)
home_city = output.config.home_city                 (departure/arrival label for trip routes)
tier1     = output.cities.tier1                     (must all be covered)
cached    = output.cached_events                    (already in cache — skip re-discovering)
done_q    = output.searches_this_week               (queries already run this week — skip)
qvars     = output.suggested_queries.vars           (substitution variables for templates)
broad_q   = output.suggested_queries.broad          (4 templates — fill {placeholders} from qvars)
tgt_tmpl  = output.suggested_queries.targeted_template  ({city} and {date} are placeholders)
```

### Step 2: Search for Events

**If invoked with `--cached-only`**: skip this entire step. Proceed directly to Step 3
using only the `cached` events from Step 1.

**Offline pre-check (no tool calls):** Review `cached`. If it already has events for
every city in `tier1` for the target weekend, skip directly to Step 3.

**Budget: max 8 searches + max 10 fetches = 18 WebSearch/WebFetch calls.**
Bash CLI calls (`save`, `log-search`, etc.) are free — they do not count.

**Log pattern** — call after every search or aggregator fetch:
```bash
python -m weekend_scout log-search \
  --query "<query_or_url>" --target-weekend "<saturday>" \
  --cities '["<city>"]' \
  --phase <broad|aggregator|targeted|verification> \
  --result-count <N>
```

**Event schema** — required fields for `save` (optional fields improve scoring):
```
Required: event_name (str), city (str), start_date (YYYY-MM-DD)
Scoring:  confidence ("confirmed"|"likely"|"unverified"), category (str),
          free_entry (bool), source_url (str), source_name (str)
Optional: end_date, time_info, location_name, lat, lon, description, country
```

---

**Phase A — Broad sweep (3–5 searches):**
For each template in `broad_q`: fill it → `query = template.format(**qvars)`.
Skip if `query` is already in `done_q`. Run WebSearch(query).

After each search, examine results:
- Specific event title (name + city + date) → record it immediately
- Aggregator URL listing many events → queue for Phase B
- Irrelevant (museums, indoor, wrong dates) → skip

Log each search with `--phase broad`.

**Phase B — Aggregator deep-dive (3–8 fetches):**
Fetch the most promising aggregator URLs. Use this prompt:

> "List ALL outdoor events, festivals, fairs, markets, city days, reenactments, food
> festivals, and street events happening on [DATES] within the area covered by this page.
> For each: event name, city, venue, dates/times, 1-sentence description, free entry or not.
> Exclude: museums, galleries, theaters, cinemas, indoor events, weekly markets."

Log each fetch with `--phase aggregator`.

**Phase C — Targeted city searches (only if needed):**
For each city in `tier1` with zero events (across `cached` + Phase A+B results):
fill → `query = tgt_tmpl.format(city=city_name, date=qvars["date"])`.
Skip if `query` is in `done_q`. Run WebSearch(query).
Same formula for any city discovered mid-search that isn't in tier1.
Log with `--phase targeted`.

**Phase D — Verification (1–3 fetches):**
For your top 5 candidate events, fetch the official source to confirm dates and details.
Update `confidence` to `"confirmed"`. Log with `--phase verification`.

---

Save ALL discovered events (including future-weekend finds):
```bash
python -m weekend_scout save --events '<JSON array>'
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
Select: top 3 in home city + up to 3 road trip options from nearby cities.

### Step 4: Build Trip Options

For road trips, use tier as a distance proxy (tier1 = nearest, tier3 = farthest):
- Option A: Easy day trip — tier1 city (single city, under 2h drive)
- Option B: Full day trip — tier1/tier2 city in a loop
- Option C: Longer trip — tier2/tier3 city or multi-stop

For each trip option, build a dict for `format-message`:
```json
{
  "name":   "Łódź Day Trip",
  "route":  "Warsaw → Łódź (130 km, ~1h45) → Warsaw",
  "events": "Festiwal Czterech Kultur | ul. Piotrkowska | Sat–Sun all day",
  "timing": "Leave by: 09:00 | Back by: ~20:00"
}
```

Use `home_city` as the start/end point name in the route.
Back-calculate departure time from the first event start time.

### Step 5: Format and Send

```bash
python -m weekend_scout format-message \
  --saturday "<saturday>" --sunday "<sunday>" \
  --city-events '<top_3_city_events_json>' \
  --trips '<trip_options_json>'
# → {"written": "<path>"}  — use this path for send:

python -m weekend_scout send --file "<path from written>"
```

If `{"sent": false}`: check that `telegram_bot_token` and `telegram_chat_id` are set in
config. If Telegram is not configured, display the message contents directly to the user.

### Step 6: Mark Served and Report

```bash
# Only if send succeeded ({"sent": true}):
python -m weekend_scout cache-mark-served --date "<saturday>"
```

Tell the user:
- How many events were found / how many are new vs cached
- Searches and fetches used (vs budget)
- Any Tier 1 cities with zero coverage (flag for next run)

---

### Event filter (reference)

**Include:** open-air festivals (music, food, craft, cultural), City Days, large fairs and
markets, historical reenactments, street art festivals, food truck rallies, beer/wine festivals,
outdoor concerts, open-air cinema, large sporting events with public attendance.

**Exclude:** museum openings, indoor theater/cinema/opera, conferences, small recurring weekly
farmers markets, private corporate events, ticketed indoor concerts.
Religious services are excluded, but religious festivals and processions are included.
