## Weekend Scout — post-compaction context

### Module map
- config.py   — load/save YAML config, DEFAULT_CONFIG, COUNTRY_CODE_MAP, run_setup_wizard
- cities.py   — parse GeoNames, get_city_list (tier1/2/3), generate_broad_queries, find_city_coords
- distance.py — haversine_km, next_weekend_dates, assign_tier (population-based, NOT distance)
- cache.py    — SQLite events + search log; query_events covers both Sat+Sun of target weekend
- telegram.py — send_telegram, format_scout_message, split_message (4096-char Telegram limit)
- __main__.py — CLI only; cmd_* functions call module functions and print JSON; no business logic

### `init` JSON contract (skill reads this)
config.target_weekend.{saturday,sunday}   — ISO dates
config.home_city                          — used as route label in Step 4
cities.{tier1,tier2,tier3}               — lists of city names sorted by distance
cached_events                             — already in cache, skip re-discovering
searches_this_week                        — queries already run this week, skip
suggested_queries.vars                    — {city, country, date, lang_hint, ...}
suggested_queries.broad                   — list of raw templates with {placeholders}
suggested_queries.targeted_template       — single template: fill {city} and {date}

### Query template mechanics
Phase A (broad):     query = template.format(**vars)          # vars["city"] = home city
Phase C (targeted):  query = tgt_tmpl.format(city=X, date=Y) # X = tier1/discovered city

### Key design decisions
- Tier assignment: 100% population-based (>=100k=1, 30k-99k=2, 15k-29k=3) — haversine only filters
- --city override: always bypass_cache=True + geocodes via find_city_coords (GeoNames lookup)
- home_coordinates is the distance precision lever; precise_location was removed (no geocoder)
- Budget: 8 WebSearch + 10 WebFetch = 18 total; Bash/CLI calls are free and don't count

### Live docs
- docs/backlog.md          — feature status (update IN PROGRESS -> DONE when finishing tasks)
- docs/design_changes.md   — log deviations from design doc with date + reason
- docs/weekend-scout-mvp-design.md — architecture source of truth
