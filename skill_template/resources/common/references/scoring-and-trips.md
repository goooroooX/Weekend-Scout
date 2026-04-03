# Scoring And Trips

Use this reference for Step 3 and Step 4. It defines the ranking, selection,
and trip-building contract.

## Score each event 1-10

- Category match (festival/fair = high, generic = low): `0-3`
- Scale (city-wide = high, small local = low): `0-2`
- Uniqueness (annual = high, recurring = low): `0-2`
- Confidence (confirmed = 1, likely = 0.5, unverified = 0): `0-1`
- Free entry: `0-1`
- Source quality (official = 1, aggregator = 0.5): `0-1`

## Build the ranked pools

Before Step 3, `cached_full` must already contain the full cached rows for the target weekend.

Build:

- `home_city_pool`: events in `home_city`
- `trip_city_pool`: events outside `home_city` but still within the configured travel scope

For `trip_city_pool`, exclude:

- out-of-radius cities
- indoor events
- weakly relevant events
- events too uncertain to justify a trip

Select from those shortlists:

- top `max_city_options` in home city
- up to `max_trip_options` road trip options from nearby cities, preferring tier1 first, then tier2, then tier3

`score_summary.total_pool` must describe the actual ranked pool before final selection, not just the displayed result count.

After selecting, compute:

```text
total_events = len(city_events_selected) + len(trip_options)
```

#@IF !codex
```bash
python -m weekend_scout score-summary --run-id "<run_id>" \
  --target-weekend "<saturday>" \
  --total-pool <N> \
  --city-events-selected <N> \
  --trip-options <N>
```
#@ENDIF
#@IF codex
```bash
python -m weekend_scout score-summary --run-id "<run_id>" \
  --target-weekend "<saturday>" \
  --total-pool <N> \
  --city-events-selected <N> \
  --trip-options <N>
```
#@ENDIF

## Build trip options

Build trip options procedurally:

1. Group candidate weekend events by city using `trip_city_pool`.
2. Exclude `home_city` from trip building.
3. Keep only cities that have at least one confirmed or otherwise strong outdoor weekend event.
4. Build at most one trip option per city.
5. Rank candidate cities by tier order first, then event quality.
6. Build up to `max_trip_options`, aiming for at least three credible trip options when the discovered pool supports it.
7. If one event clearly dominates for a city, use one event in the trip summary.
8. If multiple events materially improve the same city trip, combine at most `2-3` concise items.
9. Do **not** invent trip bundles from unrelated weak findings.
10. If fewer than three credible trip cities exist, say so explicitly and build the best available smaller set without padding.

For road trips, use tier as a distance proxy:

- tier1 = largest / closest
- tier3 = smallest / farthest

Label trips `01` through `NN` in the final message only.

Trip payload contract:

```json
{
  "name": "Lodz Day Trip",
  "route": "Warsaw -> Lodz (130 km, ~1h45) -> Warsaw",
  "events": "Spring Fair | Main Square | Sat-Sun all day",
  "timing": "Leave by: 10:00 | Back by: ~20:00",
  "url": "https://example.com/event"
}
```

Use `home_city` as the route start/end label.

"Leave by" timing means the latest departure that still arrives when the event is in full swing:

- formula: `event_start + 1h30 - drive_time`
- minimum departure: `09:00`
- if the event has no known start time, use `09:30`
