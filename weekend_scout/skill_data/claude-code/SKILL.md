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

> **Normal run rule:** During a normal scout run, do **not** inspect `weekend_scout` package
> source files to infer schemas, payload shapes, or behavior. Follow this skill as the contract.
> If the documented contract seems insufficient or inconsistent, stop the run and tell the user
> the skill needs maintenance. Source inspection is only allowed for explicit maintenance or
> debugging tasks, not during scouting.
>
> Note: `weekend_scout` is a Python package -- `python -m weekend_scout` works from any
> directory. Do **not** prefix commands with `cd <path> &&`.
> Do not patch behavior ad hoc during execution.


---

### Step 1: Initialize

```bash
python -m weekend_scout init-skill [--city CITY] [--radius KM]
```

**1a. Check for setup issues before extracting variables:**

- If `"needs_setup": true` --> run the **full setup flow** (1b).
- If `output.warnings` contains `"coordinates_not_set"` --> run the **auto-fix flow** (1c).
- Otherwise --> skip to **variable extraction** (1d).

**1b. Full setup flow** (`needs_setup: true`):

Ask the user:

> "Weekend Scout needs a quick one-time setup.
> What city do you live in? (Include the country if the name is common across countries,
> e.g. 'Lyon, France'.) How far are you willing to drive for a day trip? (default: 150 km)"

Wait for the reply. Parse: `setup_city`, optional `setup_country`, `setup_radius` (default 150).
Then proceed to **resolve coordinates** (1d-resolve).

**1c. Auto-fix flow** (`coordinates_not_set`):

Set `setup_city = output.config.home_city`, `setup_country = output.config.home_country`,
`setup_radius = output.config.radius_km`. No user question needed -- tell the user:
*"Resolving coordinates for `<setup_city>`..."*
Then proceed to **resolve coordinates** (1d-resolve).

**1d-resolve. Resolve coordinates** (used by both 1b and 1c):

```bash
python -m weekend_scout find-city --name "<setup_city>" [--country "<setup_country>"]
```

- **No matches** or `"warning"` in output: WebSearch
  `"<setup_city> city coordinates latitude longitude"` --> extract lat, lon, country.
- **Exactly 1 match**: use it.
- **Multiple matches** (different countries): list them and ask the user which country;
  use the chosen result.

Once resolved:
Use the resolved match's `language` value for the `search_language` field in the setup payload.
```bash
python -m weekend_scout setup --json '{"home_city":"<n>","home_country":"<country>","home_coordinates":{"lat":<lat>,"lon":<lon>},"radius_km":<radius>,"search_language":"<language>"}'
```

Tell the user: *"Configured -- scouting near <city>, <country>."*
Then re-run `python -m weekend_scout init-skill` and continue from 1d below.

**1d. Variable extraction:**

The `init-skill` JSON contains all config fields you need -- do **not** run `config` separately.

Extract these fields from the JSON output and keep them in mind throughout:

```
saturday     = output.config.target_weekend.saturday   (ISO date)
sunday       = output.config.target_weekend.sunday     (ISO date)
home_city    = output.config.home_city                 (departure/arrival label for trip routes)
max_city_options = output.config.max_city_options      (max home-city events to include)
max_trip_options = output.config.max_trip_options      (max road-trip options to include)
max_searches = output.config.max_searches              (search budget limit)
max_fetches  = output.config.max_fetches               (fetch budget limit)
tier1        = output.cities.tier1                     (largest nearby cities as "<city>|<country_code>")
tier2        = output.cities.tier2                     (medium-population nearby cities as "<city>|<country_code>")
tier3        = output.cities.tier3                     (smallest nearby cities as "<city>|<country_code>")
cached_count = output.cached.count                     (number of cached weekend events)
cached_covered_cities = output.cached.covered_cities   (cities already covered by weekend cache)
cached_city_counts = output.cached.city_counts         (per-city cached event counts)
done_q       = output.searches_this_week               (queries already run this week -- skip)
run_id         = output.run_id                           (pass to all log-search and log-action calls)
exclude_served = output.config.exclude_served           (bool -- if true, cached excludes already-sent events)
qvars          = output.suggested_queries.vars           (substitution variables for templates)
broad_q      = output.suggested_queries.broad          (4 templates -- fill {placeholders} from qvars)
tgt_by_country = output.suggested_queries.targeted_by_country  (per-country targeted templates with localized dates)
```

Before targeted searches, split each tier entry once:

```
city_entry        = "<city>|<country_code>"
city_name         = city_entry.rsplit("|", 1)[0]
city_country_code = city_entry.rsplit("|", 1)[1]
```

Use `city_name` for event city labels and log payloads.
For targeted searches, always look up `target = tgt_by_country[city_country_code]`.
Use `target.template` and `target.date` as the source of truth; do not translate or localize targeted queries yourself.

---

### Step 2: Search for Events

**If invoked with `--cached-only`**: skip this entire step. Immediately load the full cached
weekend event rows with:

```bash
python -m weekend_scout cache-query --date "<saturday>"
``` 

Here, `saturday` means `output.config.target_weekend.saturday` in ISO format (`YYYY-MM-DD`),
for example `2026-04-04`.

Store that result as `cached_full`, then proceed directly to Step 3 using only `cached_full`.

**Offline pre-check (no tool calls):** Review `cached_covered_cities`. If it already has events for
every city in `tier1` for the target weekend, log the skip and proceed directly to Step 3:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase search --target-weekend "<saturday>" --detail '{"reason": "all_tier1_cached"}'
```

#### 2.1 Budget and counters

**Budget: up to `max_searches` WebSearch calls + up to `max_fetches` WebFetch calls.**
Bash CLI calls (`save`, `log-search`, etc.) are free -- they do not count.

Initialize counters before Phase A:
`searches_used = 0`, `fetches_used = 0`

Initialize phase counters at the start of every phase A/B/C/D:
`phase_searches = 0`, `phase_fetches = 0`, `phase_new_events = 0`

Track usage explicitly throughout this step:
- increment `searches_used` and `phase_searches` after every WebSearch
- increment `fetches_used` and `phase_fetches` after every WebFetch
- maintain a run-level unique-event set keyed by `(event_name, city, start_date)`
- increment `phase_new_events` only when a kept event adds a new key to that set
- Before any WebSearch: stop if `searches_used >= max_searches`
- Before any WebFetch:  stop if `fetches_used  >= max_fetches`

Before every WebSearch or WebFetch:
- show the user a short progress line with:
  phase, action type, `searches_used/max_searches`, `fetches_used/max_fetches`,
  and the query or URL about to be used

**Budget allocation guidance:**
```
Phase A  (broad)        : up to 5 searches
Phase A+B combined      : up to 6 fetches total (Phase B draws from the same pool)
Phase C  (per-city)     : up to 2 searches + 1 fetch per uncovered tier1 city
                          up to 1 search per uncovered tier2 city (if searches_used < max_searches * 0.6)
                          up to 1 search per uncovered tier3 city (if searches_used < max_searches * 0.8)
Phase D  (verification) : up to 5 fetches (reserve capacity before Phase C)
```

**Event collection:** Maintain a running list of discovered events throughout
all phases. Do **not** call `save` during phases -- call it once at the end of
Step 2 with the complete list.
Use the same uniqueness rule as runtime `save_events`: an event is unique by
`event_name`, `city`, and `start_date`.

After each phase A/B/C/D:
1. Show the user a short phase summary:
   phase, `phase_searches`, `phase_fetches`, `phase_new_events`,
   and cumulative `searches_used` / `fetches_used`.
2. Write an audit summary via `log-action --action phase_summary`
   with detail containing:
   `phase`, `searches_used_in_phase`, `fetches_used_in_phase`,
   `new_events_in_phase`, `cumulative_searches_used`, `cumulative_fetches_used`.

After ALL phases complete (or are skipped), Step 6 requires a `log-action --action run_complete`
with the full budget and coverage summary. Track counters throughout so the data is ready.

#### 2.2 Reusable protocols

**SEARCH STEP** -- execute this sequence for every WebSearch:

1. **Gate:** if `searches_used >= max_searches`, do NOT search. Stop the current phase.
2. **Progress line:** print `[Phase X] WebSearch searches_used/max_searches | fetches_used/max_fetches | query: "<query>"`
3. **Execute:** `WebSearch(query)`
4. **Increment:** `searches_used += 1`, `phase_searches += 1`
5. **Extract events:** for each new unique event found, add to running list, `phase_new_events += 1`
6. **Log:** call `log-search` with `--phase <phase_label>` (see log pattern below)

Execute steps 1-6 as a unit for each search. Do NOT batch log-search calls at the end of a phase.

**FETCH STEP** -- execute this sequence for every WebFetch:

1. **Gate:** if `fetches_used >= max_fetches`, do NOT fetch. Stop the current phase.
2. **Progress line:** print `[Phase X] WebFetch searches_used/max_searches | fetches_used/max_fetches | url: "<url>"`
3. **Execute:** `WebFetch(url, prompt)` -- extract: event name, date, venue, description, free entry. Skip navigation, ads, and content unrelated to the target weekend.
4. **Increment:** `fetches_used += 1`, `phase_fetches += 1`
5. **Extract events:** for each new unique event found, add to running list, `phase_new_events += 1`
6. **Log:** call `log-search` with `--phase <phase_label>`

Execute steps 1-6 as a unit for each fetch. Do NOT batch log-search calls.

#### 2.3 Log and payload patterns

**Log pattern** -- call after every search or aggregator fetch:
```bash
python -m weekend_scout log-search \
  --query "<query_or_url>" --target-weekend "<saturday>" \
  --cities '["<city>"]' \
  --phase <broad|aggregator|targeted|verification> \
  --result-count <N> \
  --events-discovered <N> \
  --run-id "<run_id>"
```
`<N>` in `--events-discovered` is an **integer count** of newly kept unique events
from that search/fetch under the runtime dedupe rule `(event_name, city, start_date)`.
Use `0` if no new unique events were identified.

**`save` payload contract** -- `save --events` / `save --events-file` must receive a **JSON array**
of event objects. Each event object must include:
```
Required: event_name (str), city (str), start_date (YYYY-MM-DD)
Useful optional keys: confidence ("confirmed"|"likely"|"unverified"), category (str),
                      free_entry (bool), source_url (str), source_name (str),
                      end_date, time_info, location_name, lat, lon, description, country
```

**`format-message` payload contract**:
- `format-message --city-events` / `--city-events-file` must receive a **JSON array** of event dicts.
  The formatter reads:
  `event_name`, `location_name`, `start_date`, optional `end_date`, `time_info`,
  optional `description`, optional `source_url`, optional `free_entry`.
- `format-message --trips` / `--trips-file` must receive a **JSON array** of trip dicts.
  Each trip dict must contain:
  `name`, `route`, `events`, `timing`, optional `url`.

**Maintenance note:** If package behavior and this skill text ever diverge, update the skill
outside the scout run.

---

#### 2.4 Phase A -- Broad sweep (3-5 searches)

**Skip check:** fill every broad_q template via `template.format(**qvars)`. If ALL filled queries are already in `done_q`, log `skip` with reason and jump to Phase B:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase A --target-weekend "<saturday>" --detail '{"reason": "all_queries_in_done_q"}'
```

**Otherwise, execute Phase A:**

1. Log phase start:
   ```bash
   python -m weekend_scout log-action --run-id "<run_id>" --action phase_start --phase A --target-weekend "<saturday>"
   ```
2. Set `phase_searches = 0`, `phase_fetches = 0`, `phase_new_events = 0`.
3. For each template in `broad_q`:
   a. Fill it: `query = template.format(**qvars)`.
   b. Skip if `query` is already in `done_q`.
   c. Execute **SEARCH STEP** with `phase_label = broad`.
   d. After each search, examine results:
      - Specific event title (name + city + date) --> add to running list, increment `phase_new_events`.
      - Aggregator URL listing many events --> queue for Phase B.
      - Irrelevant (museums, indoor, wrong dates) --> skip.
4. Show phase summary and write `phase_summary` via `log-action --action phase_summary`.

#### 2.5 Phase B -- Aggregator deep-dive (shares Phase A's fetch budget)

**Skip check:** if no aggregator URLs were queued in Phase A, log `skip` with reason and jump to Phase C:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase B --target-weekend "<saturday>" --detail '{"reason": "no_aggregator_urls"}'
```

**Otherwise, execute Phase B:**

1. Log phase start:
   ```bash
   python -m weekend_scout log-action --run-id "<run_id>" --action phase_start --phase B --target-weekend "<saturday>"
   ```
2. Set `phase_searches = 0`, `phase_fetches = 0`, `phase_new_events = 0`.
3. For each queued aggregator URL:
   a. Execute **FETCH STEP** with `phase_label = aggregator` and this prompt:
      > "List ALL outdoor events, festivals, fairs, markets, city days, reenactments, food
      > festivals, and street events happening on [DATES] within the area covered by this page.
      > For each: event name, city, venue, dates/times, 1-sentence description, free entry or not.
      > Exclude: museums, galleries, theaters, cinemas, indoor events, weekly markets."
4. Show phase summary and write `phase_summary` via `log-action --action phase_summary`.

#### 2.6 Phase C -- Targeted city searches

**Skip check:** if all cities in all tiers are already covered (have at least one event
across `cached_covered_cities` + Phase A+B results), log `skip` with reason and jump to Phase D:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase C --target-weekend "<saturday>" --detail '{"reason": "all_cities_covered"}'
```

**Otherwise, execute Phase C:**

1. Log phase start:
   ```bash
   python -m weekend_scout log-action --run-id "<run_id>" --action phase_start --phase C --target-weekend "<saturday>"
   ```
2. Set `phase_searches = 0`, `phase_fetches = 0`, `phase_new_events = 0`.
3. Search cities in priority order: **tier1 first** (largest population), then tier2, then tier3.
   Stop when budget is exhausted.

**Rules:**
- **Always search each uncovered city individually** -- never combine multiple cities in one query.
- A city is "covered" if it has at least one event across `cached_covered_cities` + Phase A+B+C results.

**Tier 1 loop** -- for each uncovered tier1 city:

1. Split the tier entry into `city_name` and `city_country_code`.
2. Look up `target = tgt_by_country[city_country_code]`.
3. Build `query = target.template.format(city=city_name, date=target.date)`.
4. Skip if `query` is in `done_q`.
5. Execute **SEARCH STEP** with `phase_label = targeted`.
6. If the first search returns nothing useful: build a more specific query variant and execute a second **SEARCH STEP** (up to 2 searches per tier1 city).
7. Optionally: if a promising URL was found, execute **FETCH STEP** with `phase_label = targeted` (1 fetch per tier1 city max).

**Tier 2 loop** -- only if `searches_used < max_searches * 0.6`:

For each uncovered tier2 city:
1. Split entry, look up target, build query (same as tier1 steps 1-4).
2. Execute **SEARCH STEP** with `phase_label = targeted` (1 search per tier2 city).

**Tier 3 loop** -- only if `searches_used < max_searches * 0.8`:

For each uncovered tier3 city:
1. Split entry, look up target, build query (same as tier1 steps 1-4).
2. Execute **SEARCH STEP** with `phase_label = targeted` (1 search per tier3 city).

After all tiers are processed:
Show phase summary and write `phase_summary` via `log-action --action phase_summary`.
Track `uncovered_tier1` = list of tier1 city names that still have zero events after all phases.
Keep the final overall budget/result record for `log-action --action run_complete` in Step 6.

#### 2.7 Phase D -- Verification (1-5 fetches)

**Skip check:** if all top candidates already have `confidence: "confirmed"`, log `skip` and jump to save:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase D --target-weekend "<saturday>" --detail '{"reason": "all_confirmed"}'
```

**Otherwise, execute Phase D:**

1. Log phase start:
   ```bash
   python -m weekend_scout log-action --run-id "<run_id>" --action phase_start --phase D --target-weekend "<saturday>"
   ```
2. Set `phase_searches = 0`, `phase_fetches = 0`, `phase_new_events = 0`.
3. Select the top 5 most promising candidate events (not yet confirmed).
4. For each candidate with a known source URL:
   a. Do NOT re-fetch a URL already fetched in this run.
   b. Execute **FETCH STEP** with `phase_label = verification`.
   c. Update `confidence` to `"confirmed"` if dates/details match.
5. Show phase summary and write `phase_summary` via `log-action --action phase_summary`.

#### 2.8 Save discovered events

Save ALL discovered events (including future-weekend finds) as one JSON array matching the
`save` payload contract above:
```bash
python -m weekend_scout save --run-id "<run_id>" --events '<JSON array>'
```

---

### Step 3: Score and Rank

Before Step 3, load the full cached weekend event rows once with:

```bash
python -m weekend_scout cache-query --date "<saturday>"
``` 

Here, `saturday` means the same ISO Saturday date from `init-skill`
(`output.config.target_weekend.saturday`), for example `2026-04-04`.

If `cached_full` was already loaded in Step 2 (via the `--cached-only` path), skip this call.

Store that result as `cached_full` and combine `cached_full` + newly saved events for ranking.

Score each event 1-10:
- Category match (festival/fair = high, generic = low): 0-3
- Scale (city-wide = high, small local = low): 0-2  *(infer from description)*
- Uniqueness (annual = high, recurring = low): 0-2  *(infer from description)*
- Confidence (confirmed=1, likely=0.5, unverified=0): 0-1
- Free entry: 0-1
- Source quality (official=1, aggregator=0.5): 0-1

Select: top `max_city_options` in home city + up to `max_trip_options` road trip options from nearby cities (tier1 first, then tier2, tier3).

After selecting, compute: `total_events = len(city_events_selected) + len(trip_options)`

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action score_summary \
  --target-weekend "<saturday>" \
  --detail '{"total_pool": <N>, "city_events_selected": <N>, "trip_options": <N>}'
```

### Step 4: Build Trip Options

For road trips, use tier as a distance proxy (tier1 = largest/closest, tier3 = smallest/farthest):
Build up to `max_trip_options` options -- one per city that has confirmed events, working through tier1 --> tier2 --> tier3.
Label them `01` through `NN` in the final message only.
(`NN` = the sequential number of the last trip, e.g. `01`-`06` for six trips.)

For each trip option, build a dict that matches the `format-message` trip payload contract:
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
full swing** (not at opening). Formula: `event_start + 1h30 - drive_time`.
Minimum departure: **09:00** (never suggest leaving before 09:00).
Example: event opens at 10:00, drive 1h30 --> peak at 11:30 --> leave by **10:00** (not 08:30).
If the event has no known start time, use **09:30** as default departure.
`url` is optional -- include it when you have an official event URL (renders as `[link]` in the message).

### Step 5: Format and Send

Pass the selected top home-city event dicts directly as the `city-events` JSON array, and pass
trip option dicts that strictly match the trip payload contract above.
The `format-message` response returns both:
- `written`: HTML message file path for Telegram sending
- `preview`: plain-text digest preview for showing in the conversation

```bash
python -m weekend_scout format-message \
  --saturday "<saturday>" --sunday "<sunday>" \
  --city-events '<top_city_events_json>' \
  --trips '<trip_options_json>' \
  --run-id "<run_id>" \
  [--low-results true]   # include this flag when total_events < 3
# --> {"written": "<path>", "preview": "<plain text>"}  -- use `written` for send and `preview` for the user:

python -m weekend_scout send --file "<path from written>" --run-id "<run_id>"
```

**Always display the message to the user** -- show the `preview` text returned by
`format-message`. Do **not** read the written HTML file back into the conversation.

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

If `{"sent": true}`:
- run `python -m weekend_scout cache-mark-served --date "<saturday>"`
  where `saturday` is the ISO Saturday date from `init-skill` (for example `2026-04-04`)
- set `served_marked = true`, `send_reason = "sent"`

If `{"sent": false}` because Telegram is not configured:
- do **not** mark served
- set `served_marked = false`, `send_reason = "telegram_not_configured"`

If `{"sent": false}` because Telegram sending failed:
- do **not** mark served
- set `served_marked = false`, `send_reason = "send_failed"`

After the send/no-send outcome is known, **always** log `run_complete`:
```bash
python -m weekend_scout log-action --run-id "<run_id>" --action run_complete \
  --target-weekend "<saturday>" \
  --detail '{"events_sent": <city_count + trip_count>, "new_events": <N>, "cached_events": <N>, "searches_used": <N>, "max_searches": <N>, "fetches_used": <N>, "max_fetches": <N>, "sent": <true|false>, "send_reason": "<sent|telegram_not_configured|send_failed>", "served_marked": <true|false>, "uncovered_tier1": ["<city>", "<city>"]}'
```

Tell the user:
- How many events were found / how many are new vs cached
- Budget used: `searches_used`/`max_searches` searches, `fetches_used`/`max_fetches` fetches
- Any cities with zero coverage (tier1 most important -- flag for next run)

**If `total_events < 3`**, also tell the user:
> Only N event(s) found. To discover more, increase your search budget (default is 30):
> ```
> python -m weekend_scout config max_searches NN
> python -m weekend_scout config max_fetches NN
> ```

---

### Event filter (reference)

**Include:** open-air festivals (music, food, craft, cultural), City Days, large fairs and
markets, historical reenactments, street art festivals, food truck rallies, beer/wine festivals,
outdoor concerts, open-air cinema, large sporting events with public attendance.

**Exclude:** museum openings, indoor theater/cinema/opera, conferences, small recurring weekly
farmers markets, private corporate events, ticketed indoor concerts.
Religious services are excluded, but religious festivals and processions are included.
