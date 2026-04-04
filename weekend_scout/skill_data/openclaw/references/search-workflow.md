# Search Workflow

Use this reference for Step 2 only. It defines the exact discovery contract.
Do **not** inspect package source or call `--help` during a normal run.

## Hard rules

- Execute phases strictly in this order: `A -> B -> C -> D -> save -> cache-query -> score -> format/send`.
- Do **not** perform any `WebSearch` or `WebFetch` after Phase D completes.
- Do **not** call `cache-query` before `save` except in the documented cached-only path.
- Every phase must end with either a `skip` log or a `phase_summary` log before moving on.
- Do not silently abandon tier loops while budget remains; if you stop early, state the reason.
- Do **not** stop early just because some events were found.
- If uncovered tier1 cities remain, continue searching while budget remains.
- If home-city picks are still below `max_city_options` or there are fewer than three credible trip cities, continue into the next eligible city/tier while thresholds allow.
- Tier2 and tier3 are requested on demand. Do **not** preload or infer later-tier city queues from earlier context.

## Event filter

Include:

- open-air festivals (music, food, craft, cultural)
- City Days and town celebrations
- large fairs and markets
- historical reenactments and outdoor spectacles
- street art festivals and performer festivals
- food truck rallies, beer festivals, wine festivals
- outdoor concerts and open-air cinema
- large sporting events with public attendance
- religious festivals and processions

Exclude:

- museum openings, gallery exhibitions
- indoor theater, cinema, opera, and conferences
- small recurring weekly farmers markets
- private corporate events
- ticketed indoor concerts
- religious services

## Cached-only path

If invoked with `--cached-only`:

```bash
python -m weekend_scout cache-query --date "<saturday>"
```

Here, `saturday` means `output.config.target_weekend.saturday` in ISO format (`YYYY-MM-DD`),
for example `2026-04-04`.

Store that result as `cached_full`, then proceed directly to Step 3 using only `cached_full`.

## Offline pre-check

If `cached_covered_cities` already covers every city in `tier1`, log the skip and proceed
directly to Step 3:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase search --target-weekend "<saturday>" --detail '{"reason": "all_tier1_cached"}'
```

## Budget and counters

Budget: up to `max_searches` `WebSearch` calls and up to `max_fetches` discovery `WebFetch`
calls during Phases A-C. Phase D gets a separate fixed validation reserve from
`workflow.phase_d.validation_fetch_limit`. Bash/CLI calls are free.

Initialize before Phase A:

- `searches_used = 0`
- `fetches_used = 0`
- `validation_fetches_used = 0`
- `validation_fetch_limit = workflow.phase_d.validation_fetch_limit`

Initialize at the start of every phase A/B/C/D:

- `phase_searches = 0`
- `phase_fetches = 0`
- `phase_new_events = 0`

Track usage explicitly:

- Increment `searches_used` and `phase_searches` after every `WebSearch`.
- Increment `fetches_used` and `phase_fetches` after every discovery `WebFetch` in Phases B/C.
- Increment `validation_fetches_used` and `phase_fetches` after every verification `WebFetch` in Phase D.
- Maintain a run-level unique-event set keyed by `(event_name, city, start_date)`.
- Increment `phase_new_events` only when a kept event adds a new key to that set.
- Before any `WebSearch`, stop if `searches_used >= max_searches`.
- Before any discovery `WebFetch`, stop if `fetches_used >= max_fetches`.
- Before any verification `WebFetch`, stop if `validation_fetches_used >= validation_fetch_limit`.

Before every `WebSearch` or `WebFetch`, show the user a short progress line with:

- phase
- action type
- `searches_used/max_searches`
- `fetches_used/max_fetches` for discovery fetches in Phases B/C
- `validation_fetches_used/validation_fetch_limit` for verification fetches in Phase D
- the exact query or URL about to be used

### Status line templates

Use these templates verbatim. Substitute the actual counters and query/URL values,
and do **not** add extra prose on the same line.

- `SEARCH STATUS`

```text
STATUS phase=<A|C> action=WebSearch searches=<searches_used>/<max_searches> fetches=<fetches_used>/<max_fetches> target="<query>"
```

- `DISCOVERY FETCH STATUS`

```text
STATUS phase=<B|C> action=WebFetch searches=<searches_used>/<max_searches> fetches=<fetches_used>/<max_fetches> target="<url>"
```

- `VALIDATION FETCH STATUS`

```text
STATUS phase=D action=WebFetch searches=<searches_used>/<max_searches> fetches=<fetches_used>/<max_fetches> validation_fetches=<validation_fetches_used>/<validation_fetch_limit> target="<url>"
```

Budget allocation guidance:

```text
Phase A (broad): up to 5 searches
Phase A+B combined: up to 6 discovery fetches total
Phase C (per-city):
  tier1: up to 2 searches + 1 discovery fetch per uncovered tier1 city
  tier2: after tier1, sweep every uncovered tier2 city in emitted order while main search budget remains
  tier3: after tier2, sweep every uncovered tier3 city in emitted order while main search budget remains
Phase D (verification): up to 5 validation fetches from the fixed reserve
```

## SEARCH STEP

For every `WebSearch`, execute this sequence exactly:

1. Gate on `searches_used >= max_searches`.
2. Show the exact `SEARCH STATUS` line.
3. Execute `WebSearch(query)`.
4. Increment `searches_used` and `phase_searches`.
5. Keep only relevant outdoor weekend events.
6. Log immediately with `log-search`.
7. Do **not** start another web action until the matching `log-search` succeeds.

Do not batch `log-search` calls at the end of a phase. The `log-search` must succeed before the next `WebSearch` or `WebFetch`.

## FETCH STEP

For every `WebFetch`, execute this sequence exactly:

1. Gate on the correct fetch budget:
   - discovery fetch in Phases B/C: stop if `fetches_used >= max_fetches`
   - verification fetch in Phase D: stop if `validation_fetches_used >= validation_fetch_limit`
2. Show the exact status line for the current fetch type:
   - discovery fetch in Phases B/C: show the exact `DISCOVERY FETCH STATUS` line
   - verification fetch in Phase D: show the exact `VALIDATION FETCH STATUS` line
3. Execute `WebFetch(url, prompt)`.
4. Increment the correct counter and `phase_fetches`:
   - discovery fetch in Phases B/C: increment `fetches_used`
   - verification fetch in Phase D: increment `validation_fetches_used`
5. Keep only relevant outdoor weekend events.
6. Log immediately with `log-search`.
7. Do **not** start another web action until the matching `log-search` succeeds.

Use only `FETCH STEP` for queued page extraction in Phase B and Phase D.

## Log and payload patterns

After every search or fetch, call `log-search`.

- Broad searches must log `cities = [home_city]`.
- Targeted and verification searches/fetches must log `cities = [city_name]` for the city being worked.

```bash
python -m weekend_scout log-search \
  --query "<query_or_url>" --target-weekend "<saturday>" \
  --cities '["<city>"]' \
  --phase <broad|aggregator|targeted|verification> \
  --result-count <N> \
  --events-discovered <N> \
  --run-id "<run_id>"
```

`events-discovered` must be an integer count of newly kept unique events from that single search or fetch.
Use `0` if the action produced no new unique events.

`save` must receive one JSON array of event objects. Minimal required keys:

```text
event_name, city, start_date
```

Useful optional keys:

```text
confidence, category, free_entry, source_url, source_name,
end_date, time_info, location_name, lat, lon, description, country
```

## Phase lifecycle and helper success

Start any phase with:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start \
  --phase <A|B|C|D> --target-weekend "<saturday>"
```

End any completed phase with `phase-summary`, which computes the canonical detail payload from logged discovery actions.

```bash
python -m weekend_scout phase-summary --run-id "<run_id>" --phase <A|B|C|D> --target-weekend "<saturday>"
```

Required Step 2 CLI calls must succeed before discovery continues. If any such call exits non-zero,
returns a top-level `error`, or returns a required-success payload indicating failure, stop the run
and report contract drift. Do **not** repair failed Step 2 state by retroactive logging or manual
payload synthesis.

## Phase A: Broad sweep

Use `workflow.phase_a.queries` in the emitted order.

Skip check: if every broad query card is already marked `query_already_done`, log `skip` for Phase A and jump to Phase B.

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase A --target-weekend "<saturday>" --detail '{"reason": "all_queries_in_done_q"}'
```

Otherwise:

1. Log Phase A start:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start \
  --phase A --target-weekend "<saturday>"
```

2. Reset phase counters.
3. For each broad query card:
   - skip cards already marked `query_already_done`
   - execute `SEARCH STEP` with `phase_label = broad`
   - keep direct event hits immediately
   - queue aggregator URLs for Phase B
4. Show the short Phase A summary to the user.
5. End Phase A with:

```bash
python -m weekend_scout phase-summary --run-id "<run_id>" --phase A --target-weekend "<saturday>"
```

6. After Phase A completes, continue only to Phase B.

## Phase B: Aggregator deep-dive

Skip if no aggregator URLs were queued in Phase A.

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase B --target-weekend "<saturday>" --detail '{"reason": "no_aggregator_urls"}'
```

Otherwise:

1. Log Phase B start:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start \
  --phase B --target-weekend "<saturday>"
```

2. Reset phase counters.
3. For each queued aggregator URL, execute `FETCH STEP` with `phase_label = aggregator` and this prompt:

Queued aggregator URL work in Phase B uses the exact `DISCOVERY FETCH STATUS` line.

> "List ALL outdoor events, festivals, fairs, markets, city days, reenactments, food
> festivals, and street events happening on [DATES] within the area covered by this page.
> For each: event name, city, venue, dates/times, 1-sentence description, free entry or not.
> Exclude: museums, galleries, theaters, cinemas, indoor events, weekly markets."

4. Keep only events within the configured travel scope and useful for this run.
5. Out-of-scope hits may be mentioned as discarded evidence, but must not be saved as usable trip candidates.
6. Phase B is URL-based extraction. Use only `FETCH STEP` for queued page work, not ad hoc substitute search-only flows.
7. Broad or aggregator hits outside the radius do **not** justify ending targeted search if nearby-city coverage is still weak.
8. Show the short Phase B summary to the user.
9. End Phase B with:

```bash
python -m weekend_scout phase-summary --run-id "<run_id>" --phase B --target-weekend "<saturday>"
```

## Phase C: Targeted city searches

Use `workflow.phase_c.tier1` first. Request tier2 and tier3 on demand only after the earlier tier is finished.

Rules:

- Always search each uncovered city individually.
- A city is covered if it has at least one event across `cached_covered_cities` plus Phase A/B/C results.
- Follow the emitted tier order exactly.
- Do **not** skip tier2 or tier3 because coverage looks good elsewhere. Sweep later tiers deterministically while main search budget remains.

If all cities in all tiers are already covered, log `skip` for Phase C and jump to Phase D.

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase C --target-weekend "<saturday>" --detail '{"reason": "all_cities_covered"}'
```

Otherwise:

1. Log Phase C start:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start \
  --phase C --target-weekend "<saturday>"
```

2. Reset phase counters.
3. Search cities in priority order: tier1 first, then tier2, then tier3. Stop only when the main search budget is exhausted or the current tier is fully exhausted.

Tier 1:

- Use each tier1 card base query first.
- For each tier1 card, execute `SEARCH STEP` with `phase_label = targeted`.
- Targeted searches in Phase C use the exact `SEARCH STATUS` line with `phase=C`.
- If the first search returns nothing useful, build one more specific second query variant and run one more `SEARCH STEP` with `phase_label = targeted`.
- If a promising URL appears, use at most one targeted `FETCH STEP` with `phase_label = targeted` for that city.
- Any targeted fetch in Phase C uses the exact `DISCOVERY FETCH STATUS` line with `phase=C`.

Tier 2:

- After tier1, request tier2 batches while `searches_used < max_searches`.
- Request the next batch explicitly:
```bash
python -m weekend_scout phase-c-cities --run-id "<run_id>" --tier 2 \
  --offset <offset> --limit 6 \
  --covered-cities '["<city>", "<city>"]'
```
- Use only the returned batch cards.
- Tier2 targeted searches in Phase C use the exact `SEARCH STATUS` line with `phase=C`.
- Any targeted fetch in tier2 uses the exact `DISCOVERY FETCH STATUS` line with `phase=C`.
- Finish and log the current batch before requesting the next one.
- If a batch returns `has_more = true` and `searches_used < max_searches`, request the next tier2 batch.
- If the batch returns `has_more = false`, tier2 is exhausted; continue to tier3 if main search budget remains.
- Phase C stays open while tier2 batches run. Do **not** log another `phase_start` for a later-tier batch.
- Do **not** call `phase-summary` between tier batches. Keep Phase C open while you request more cities.

Tier 3:

- After tier2 is exhausted, request tier3 batches while `searches_used < max_searches`.
```bash
python -m weekend_scout phase-c-cities --run-id "<run_id>" --tier 3 \
  --offset <offset> --limit 6 \
  --covered-cities '["<city>", "<city>"]'
```
- Use only the returned batch cards.
- Tier3 targeted searches in Phase C use the exact `SEARCH STATUS` line with `phase=C`.
- Any targeted fetch in tier3 uses the exact `DISCOVERY FETCH STATUS` line with `phase=C`.
- Finish and log the current batch before requesting the next one.
- If a batch returns `has_more = true` and `searches_used < max_searches`, request the next tier3 batch.
- If the batch returns `has_more = false`, tier3 is exhausted.
- Phase C stays open while tier3 batches run. Do **not** log another `phase_start` for a later-tier batch.
- Do **not** call `phase-summary` between tier batches. Keep Phase C open while you request more cities.

After all tiers:

- Show the short Phase C summary to the user.
- End Phase C with:

```bash
python -m weekend_scout phase-summary --run-id "<run_id>" --phase C --target-weekend "<saturday>"
```

- Track `uncovered_tier1` for Step 6.
- Do not start Phase D until Phase C ends with `phase-summary` or `skip`.

## Phase D: Verification

Use the fixed validation reserve from `workflow.phase_d.validation_fetch_limit`.
Do **not** count Phase D fetches against `max_fetches`.

Skip if all top candidates are already `confidence: "confirmed"`.

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase D --target-weekend "<saturday>" --detail '{"reason": "all_confirmed"}'
```

Otherwise:

1. Log Phase D start:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start \
  --phase D --target-weekend "<saturday>"
```

2. Reset phase counters.
3. Select the top five most promising unconfirmed candidate events.
4. For each candidate with a known source URL:
   - verification fetches in Phase D use the exact `VALIDATION FETCH STATUS` line
   - the `VALIDATION FETCH STATUS` line must include `validation_fetches_used/validation_fetch_limit`
   - do not re-fetch a URL already fetched in this run
   - execute `FETCH STEP` with `phase_label = verification`
   - update `confidence` to `"confirmed"` only when the source matches the timing/details
5. Show the short Phase D summary to the user.
6. End Phase D with:

```bash
python -m weekend_scout phase-summary --run-id "<run_id>" --phase D --target-weekend "<saturday>"
```


After Phase D completes, discovery work is over. Do not return to targeted or broad searching.

## Save after discovery

Save all discovered events once, after discovery is complete.

```bash
python -m weekend_scout save --run-id "<run_id>" --events '<JSON array>'
```

Then load cached rows once with:

```bash
python -m weekend_scout cache-query --date "<saturday>"
```

Store that result as `cached_full` and proceed to scoring.
