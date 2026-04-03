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

Before writing the detail payload, read `references/platform-codex.md`.
Write `{"reason": "all_tier1_cached"}` to `detail_json_path`, then run:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase search --target-weekend "<saturday>" --detail-file "$detail_json_path"
```

## Budget and counters

Budget: up to `max_searches` `WebSearch` calls and up to `max_fetches` `WebFetch` calls.
Bash/CLI calls are free.

Initialize before Phase A:

- `searches_used = 0`
- `fetches_used = 0`

Initialize at the start of every phase A/B/C/D:

- `phase_searches = 0`
- `phase_fetches = 0`
- `phase_new_events = 0`

Track usage explicitly:

- Increment `searches_used` and `phase_searches` after every `WebSearch`.
- Increment `fetches_used` and `phase_fetches` after every `WebFetch`.
- Maintain a run-level unique-event set keyed by `(event_name, city, start_date)`.
- Increment `phase_new_events` only when a kept event adds a new key to that set.
- Before any `WebSearch`, stop if `searches_used >= max_searches`.
- Before any `WebFetch`, stop if `fetches_used >= max_fetches`.

Before every `WebSearch` or `WebFetch`, show the user a short progress line with:

- phase
- action type
- `searches_used/max_searches`
- `fetches_used/max_fetches`
- the exact query or URL about to be used

Budget allocation guidance:

```text
Phase A (broad): up to 5 searches
Phase A+B combined: up to 6 fetches total
Phase C (per-city):
  tier1: up to 2 searches + 1 fetch per uncovered tier1 city
  tier2: up to 1 search per uncovered tier2 city when searches_used < max_searches * 0.6
  tier3: up to 1 search per uncovered tier3 city when searches_used < max_searches * 0.8
Phase D (verification): up to 5 fetches
```

## SEARCH STEP

For every `WebSearch`, execute this sequence exactly:

1. Gate on `searches_used >= max_searches`.
2. Show the progress line.
3. Execute `WebSearch(query)`.
4. Increment `searches_used` and `phase_searches`.
5. Keep only relevant outdoor weekend events.
6. Log immediately with `log-search`.
7. Do **not** start another web action until the matching `log-search` succeeds.

Do not batch `log-search` calls at the end of a phase. The `log-search` must succeed before the next `WebSearch` or `WebFetch`.

## FETCH STEP

For every `WebFetch`, execute this sequence exactly:

1. Gate on `fetches_used >= max_fetches`.
2. Show the progress line.
3. Execute `WebFetch(url, prompt)`.
4. Increment `fetches_used` and `phase_fetches`.
5. Keep only relevant outdoor weekend events.
6. Log immediately with `log-search`.
7. Do **not** start another web action until the matching `log-search` succeeds.

Use only `FETCH STEP` for queued page extraction in Phase B and Phase D.

## Log and payload patterns

After every search or fetch, call `log-search`.

- Broad searches must log `cities = [home_city]`.
- Targeted and verification searches/fetches must log `cities = [city_name]` for the city being worked.

Before writing the cities payload, read `references/platform-codex.md`.
Write a fresh payload file immediately before each `log-search` call. Never reuse a path that may have been auto-deleted by the CLI.
Use a `_tmp_*.tmp` filename for each transport payload in this step, for example `_tmp_cities.tmp`, `_tmp_detail.tmp`, or `_tmp_events.tmp`.
Write the covered city list JSON array to `cities_json_path`, then run:

```bash
python -m weekend_scout log-search \
  --query "<query_or_url>" --target-weekend "<saturday>" \
  --cities-file "$cities_json_path" \
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

## Phase lifecycle commands

Start any phase with:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action phase_start \
  --phase <A|B|C|D> --target-weekend "<saturday>"
```

End any completed phase with `phase-summary`, which computes the canonical detail payload from logged discovery actions.

```bash
python -m weekend_scout phase-summary --run-id "<run_id>" --phase <A|B|C|D> --target-weekend "<saturday>"
```

## Phase A: Broad sweep

Use `workflow.phase_a.queries` in the emitted order.

Skip check: if every broad query card is already marked `query_already_done`, log `skip` for Phase A and jump to Phase B.

Write `{"reason": "all_queries_in_done_q"}` to `detail_json_path`, then run:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase A --target-weekend "<saturday>" --detail-file "$detail_json_path"
```

Otherwise:

1. Log Phase A start.
2. Reset phase counters.
3. For each broad query card:
   - skip cards already marked `query_already_done`
   - execute `SEARCH STEP`
   - keep direct event hits immediately
   - queue aggregator URLs for Phase B
4. End Phase A with `phase-summary`.
5. After Phase A completes, continue only to Phase B.

## Phase B: Aggregator deep-dive

Skip if no aggregator URLs were queued in Phase A.

Write `{"reason": "no_aggregator_urls"}` to `detail_json_path`, then run:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase B --target-weekend "<saturday>" --detail-file "$detail_json_path"
```

Otherwise:

1. Log Phase B start.
2. Reset phase counters.
3. For each queued aggregator URL, execute `FETCH STEP` with this prompt:

> "List ALL outdoor events, festivals, fairs, markets, city days, reenactments, food
> festivals, and street events happening on [DATES] within the area covered by this page.
> For each: event name, city, venue, dates/times, 1-sentence description, free entry or not.
> Exclude: museums, galleries, theaters, cinemas, indoor events, weekly markets."

4. Keep only events within the configured travel scope and useful for this run.
5. Out-of-scope hits may be mentioned as discarded evidence, but must not be saved as usable trip candidates.
6. Phase B is URL-based extraction. Use only `FETCH STEP` for queued page work, not ad hoc substitute search-only flows.
7. Broad or aggregator hits outside the radius do **not** justify ending targeted search if nearby-city coverage is still weak.
8. End Phase B with `phase-summary`.

## Phase C: Targeted city searches

Use `workflow.phase_c.tier1` first. Request tier2 and tier3 on demand only after the earlier tier is finished and coverage is still thin.

Rules:

- Always search each uncovered city individually.
- A city is covered if it has at least one event across `cached_covered_cities` plus Phase A/B/C results.
- Follow the emitted tier order exactly.

If all cities in all tiers are already covered, log `skip` for Phase C and jump to Phase D.

Write `{"reason": "all_cities_covered"}` to `detail_json_path`, then run:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase C --target-weekend "<saturday>" --detail-file "$detail_json_path"
```

Tier 1:

- Use each tier1 card base query first.
- If the first search returns nothing useful, build one more specific second query variant and run one more `SEARCH STEP`.
- If a promising URL appears, use at most one targeted `FETCH STEP` for that city.

Tier 2:

- Run only when `searches_used < max_searches * 0.6` and coverage is still thin.
- Request the next batch explicitly:
Before requesting the batch, read `references/platform-codex.md`, write the current covered-city array to a fresh `_tmp_covered_cities.tmp` file, then run:
```bash
python -m weekend_scout phase-c-cities --run-id "<run_id>" --tier 2 \
  --offset <offset> --limit 6 \
  --covered-cities-file "$covered_cities_path" \
  --searches-used <searches_used>
```
- Use only the returned batch cards.
- Finish and log the current batch before requesting the next one.
- Do **not** call `phase-summary` between tier batches. Keep Phase C open while you request more cities.

Tier 3:

- Run only when `searches_used < max_searches * 0.8`, tier2 is already done, and coverage is still thin.
- Request the next batch explicitly with the same `phase-c-cities` command pattern, but `--tier 3`.
- Use only the returned batch cards.
- Finish and log the current batch before requesting the next one.
- Do **not** call `phase-summary` between tier batches. Keep Phase C open while you request more cities.

After all tiers:

- End Phase C with `phase-summary`.
- Track `uncovered_tier1` for Step 6.
- Do not start Phase D until Phase C ends with `phase-summary` or `skip`.

## Phase D: Verification

Skip if all top candidates are already `confidence: "confirmed"`.

Write `{"reason": "all_confirmed"}` to `detail_json_path`, then run:

```bash
python -m weekend_scout log-action --run-id "<run_id>" --action skip \
  --phase D --target-weekend "<saturday>" --detail-file "$detail_json_path"
```

Otherwise:

1. Log Phase D start.
2. Reset phase counters.
3. Select the top five most promising unconfirmed candidate events.
4. For each candidate with a known source URL:
   - do not re-fetch a URL already fetched in this run
   - execute `FETCH STEP` with `phase_label = verification`
   - update `confidence` to `"confirmed"` only when the source matches the timing/details
5. End Phase D with `phase-summary`.

After Phase D completes, discovery work is over. Do not return to targeted or broad searching.

## Save after discovery

Save all discovered events once, after discovery is complete.

Write the discovered events array to `events_json_path`, then run:

```bash
python -m weekend_scout save --run-id "<run_id>" --events-file "$events_json_path"
```

Then load cached rows once with:

```bash
python -m weekend_scout cache-query --date "<saturday>"
```

Store that result as `cached_full` and proceed to scoring.
