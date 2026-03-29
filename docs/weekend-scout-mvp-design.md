> **This document is superseded.**
> The current reference is [docs/weekend-scout-design-v2.md](weekend-scout-design-v2.md).
> This file is kept for historical context only.

# Weekend Scout -- MVP Design Document

**Version:** 0.2
**Date:** 2026-03-26
**Status:** Design Phase (MVP)

---

## 1. Overview

**Weekend Scout** is a Claude Code skill backed by a Python CLI tool. It discovers
outdoor events, festivals, fairs, and city celebrations happening next weekend
in the user's city and within driving distance, then delivers curated trip options
to a Telegram group.

The agent does the "smart work" (searching, evaluating, deduplicating, ranking).
Python does the "dumb work" (city lists, caching, distance math, Telegram sending).
No external search APIs are required. The agent uses Claude Code's built-in
WebSearch and WebFetch tools, which are included in the Pro/Max subscription.

---

## 2. How Claude Code Web Tools Work (Design Constraints)

These constraints shape every design decision in this document.

**WebSearch** returns only page titles and URLs. No snippets, no descriptions,
no page content. Example response:

```
Links: [
  {"title": "Dni Radomia 2026 - Program imprezy", "url": "https://radom.pl/dni-radomia"},
  {"title": "Jarmarki i festyny w okolicach Warszawy", "url": "https://goout.net/..."},
  ...
]
```

Sometimes a title alone reveals the event name, city, and date. Often it does not.
The agent must decide which URLs are worth fetching.

**WebFetch** takes a URL + a mandatory question. The page content is passed through
Haiku (a fast, cheap model) which returns a summarized answer. The agent never sees
raw HTML. Example:

```
WebFetch(
  url: "https://goout.net/pl/festiwale/warszawa/...",
  prompt: "List all outdoor events, festivals, fairs happening within
           150km of Warsaw on March 28-29, 2026. For each, give:
           event name, city, dates, brief description."
)
```

Haiku returns a structured text summary. One good aggregator page can yield
10-20 events in a single fetch.

**Cost:** On Pro/Max subscription plans, web search and fetch draw from the
included usage budget. There is no separate per-search charge. The constraint is
the overall token budget per session, not a search count.

**Target budget per run:** 15-25 total tool calls (searches + fetches combined).

---

## 3. System Architecture

```
  User: /weekend-scout [city] [radius]
         |
         v
  +-----------------------+
  |  SKILL.md             |  Orchestrator prompt with search strategy,
  |  (Claude Code Skill)  |  budget constraints, scoring criteria
  +-----------------------+
         |
         | Calls Python CLI for data prep, then runs searches,
         | then calls Python CLI for output
         v
  +--------------------------------------------------+
  |              Python CLI Tool                      |
  |              ~/weekend-scout/                     |
  |                                                   |
  |  config.py ---- Config management (YAML)          |
  |  cities.py ---- City list + tier assignment        |
  |  cache.py ----- SQLite event cache + search log   |
  |  distance.py -- Straight-line distance calculator  |
  |  telegram.py -- Message formatting + sending       |
  |  main.py ------ CLI entry point                    |
  +--------------------------------------------------+
```

### Interaction Flow (single run)

```
Agent                          Python CLI                    Web
  |                               |                           |
  |-- weekend-scout init -------->|                           |
  |   (load config, check cache)  |                           |
  |<-- config + cached events ----|                           |
  |    + city list + suggested    |                           |
  |    search queries             |                           |
  |                               |                           |
  |-- WebSearch (broad sweep) ----|-------------------------->|
  |<-- titles + URLs -------------|---------------------------|
  |                               |                           |
  |-- WebFetch (aggregators) -----|-------------------------->|
  |<-- extracted event lists -----|---------------------------|
  |                               |                           |
  |-- WebSearch (city-targeted) --|-------------------------->|
  |<-- titles + URLs -------------|---------------------------|
  |                               |                           |
  |-- WebFetch (verify top picks)-|-------------------------->|
  |<-- confirmed details ---------|---------------------------|
  |                               |                           |
  |-- weekend-scout save -------->|                           |
  |   (new events to cache)       |                           |
  |<-- saved --------------------|                           |
  |                               |                           |
  |   [Agent builds trip options, |                           |
  |    scores, ranks, formats]    |                           |
  |                               |                           |
  |-- weekend-scout send -------->|                           |
  |   (formatted message)         |----> Telegram Bot API --->|
  |<-- sent ----------------------|                           |
```

---

## 4. Component Details

### 4.1 Configuration (`config.py`)

All config lives in `~/.weekend-scout/config.yaml`. Created on first run.

```yaml
# --- User Location ---
home_city: "Warsaw"
home_country: "Poland"
home_coordinates:
  lat: 52.2297
  lon: 21.0122
precise_location: "ul. Marszalkowska 1, Mokotow, Warsaw"
  # Used as route starting point. Can be address, district name,
  # or nearby known landmark.

radius_km: 150
  # Max distance from home city center.
  # Cross-border EU cities within this radius are included.

# --- Search Settings ---
search_language: "pl"
  # Derived from country. Used for query generation.
  # Agent adds 1 English query for tourist-facing sites.

# --- Event Preferences ---
include_categories:
  - festival        # music, food, craft, cultural
  - fair            # jarmark, kiermasz
  - city_days       # Dni Miasta
  - reenactment     # historical reenactments
  - street_art      # street performers, murals
  - food_festival   # food trucks, beer fests
  - open_air_show   # outdoor cinema, concerts, light shows

exclude_categories:
  - museum
  - gallery
  - theater
  - cinema
  - conference
  - recurring_market  # weekly farmers markets

# --- Output ---
max_city_options: 3      # events in home city
max_trip_options: 3      # road trip routes to nearby cities
output_language: "en"    # language of the Telegram message

# --- Telegram ---
telegram_bot_token: ""   # from @BotFather
telegram_chat_id: ""     # group/channel ID

# --- Schedule ---
auto_run: false
run_day: "friday"
run_time: "18:00"
```

**CLI interface:**

```bash
# First run: interactive setup
python -m weekend_scout setup

# Show current config
python -m weekend_scout config

# Initialize a run: returns config + cache + cities + query suggestions
python -m weekend_scout init

# Save events to cache
python -m weekend_scout save --events '<JSON array>'

# Send message to Telegram
python -m weekend_scout send --message '<formatted text>'

# Query cache for a specific weekend
python -m weekend_scout cache-query --date 2026-03-28

# Full automated run (for cron, calls Claude Code)
python -m weekend_scout run
```

### 4.2 City List Generator (`cities.py`)

**Purpose:** Generate and cache a list of cities within `radius_km` of `home_city`,
assigned to search tiers.

**Data source:** OpenStreetMap Nominatim API (free, no key required, 1 req/sec rate limit).
Query: search for `place=city` and `place=town` within a bounding box derived from
the radius.

**Alternative for MVP:** Use a pre-built dataset. GeoNames provides a free downloadable
file (`cities15000.txt`) containing all cities with population > 15,000. The Python
script filters by distance from home coordinates. This avoids any API calls.

**Recommended MVP approach:** GeoNames file, bundled with the project or downloaded once.

**Cache file:** `~/.weekend-scout/cities_{home_city}_{radius_km}.json`

**Schema:**

```json
{
  "generated": "2026-03-26T10:00:00",
  "home_city": "Warsaw",
  "radius_km": 150,
  "country": "Poland",
  "cities": [
    {
      "name": "Lodz",
      "name_local": "Łódź",
      "country": "PL",
      "lat": 51.7592,
      "lon": 19.4560,
      "population": 672185,
      "distance_km": 131,
      "tier": 1
    },
    {
      "name": "Radom",
      "name_local": "Radom",
      "country": "PL",
      "lat": 51.4027,
      "lon": 21.1471,
      "population": 210532,
      "distance_km": 92,
      "tier": 1
    },
    {
      "name": "Plock",
      "name_local": "Płock",
      "country": "PL",
      "lat": 52.5463,
      "lon": 19.7065,
      "population": 119709,
      "distance_km": 108,
      "tier": 2
    }
  ]
}
```

**Tier assignment:**

| Tier | Population     | Role in search strategy                     |
|------|----------------|---------------------------------------------|
| 1    | 100,000+       | Always searched individually if not covered  |
| 2    | 30,000-99,999  | Covered by regional queries; targeted only if gaps |
| 3    | 15,000-29,999  | Covered by regional queries only             |

**Invalidation:** Regenerate only when `home_city` or `radius_km` changes.

**Cross-border handling:** GeoNames is global. The distance filter naturally
includes EU cities across the border. The city list just includes them with
their actual country code. The agent handles search language accordingly
(e.g., German queries for German cities near Wroclaw).

**Distance calculation:** Haversine formula (straight-line). Good enough for
filtering and rough estimates. No API needed.

```python
from math import radians, sin, cos, sqrt, atan2

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))
```

**Driving time estimate (no API):** For Poland/Central Europe, a rough heuristic:

```python
def estimated_drive_minutes(distance_km):
    if distance_km < 30:
        return distance_km * 1.5     # urban, ~40 km/h avg
    elif distance_km < 80:
        return distance_km * 1.0     # mixed, ~60 km/h avg
    else:
        return distance_km * 0.75    # highway-heavy, ~80 km/h avg
```

This is intentionally simple. Accurate enough for "about 1.5 hours" estimates.
No routing API needed for MVP.

### 4.3 Event Cache (`cache.py`)

**Purpose:** SQLite database storing discovered events and a search log.
Located at `~/.weekend-scout/cache.db`.

**Why SQLite:** Zero setup, no server, file-based, Python has built-in support.
Perfect for a personal tool.

**Schema:**

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identity
    event_name TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT DEFAULT 'PL',

    -- When
    start_date TEXT NOT NULL,       -- ISO date: '2026-03-28'
    end_date TEXT,                  -- ISO date, nullable if single-day
    time_info TEXT,                 -- free text: '10:00-20:00' or 'all day'

    -- Where
    location_name TEXT,             -- 'Rynek Starego Miasta'
    lat REAL,
    lon REAL,

    -- What
    category TEXT,                  -- from config include_categories
    description TEXT,               -- 1-3 sentence summary
    free_entry BOOLEAN,

    -- Source
    source_url TEXT,
    source_name TEXT,               -- 'AllEvents', 'goout.net', etc.

    -- Meta
    discovered_date TEXT NOT NULL,  -- when the agent found this
    confidence TEXT DEFAULT 'likely',
        -- 'confirmed': fetched from official source, dates verified
        -- 'likely': from aggregator, looks correct
        -- 'unverified': from search title only, not fetched
    served BOOLEAN DEFAULT 0,       -- already sent to Telegram
    canceled BOOLEAN DEFAULT 0,

    -- Dedup
    dedup_key TEXT UNIQUE
        -- normalized: lower(event_name) + city + start_date
        -- INSERT OR IGNORE handles duplicates
);

CREATE TABLE search_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    search_date TEXT NOT NULL,       -- ISO date
    target_weekend TEXT NOT NULL,    -- '2026-03-28' (Saturday of target)
    result_count INTEGER DEFAULT 0,
    cities_covered TEXT,             -- JSON array: ["Warsaw", "Lodz"]
    phase TEXT                       -- 'broad', 'aggregator', 'targeted'
);

CREATE INDEX idx_events_dates ON events(start_date, end_date);
CREATE INDEX idx_events_city ON events(city);
CREATE INDEX idx_events_dedup ON events(dedup_key);
CREATE INDEX idx_search_log_weekend ON search_log(target_weekend);
```

**CLI commands:**

```bash
# Query: what events do we have cached for next weekend?
python -m weekend_scout cache-query --date 2026-03-28
# Returns JSON array of matching events

# Save: agent passes discovered events as JSON
python -m weekend_scout save --events '[
  {
    "event_name": "Jarmark Wielkanocny",
    "city": "Warsaw",
    "start_date": "2026-03-28",
    "end_date": "2026-03-29",
    "time_info": "10:00-20:00",
    "location_name": "Stare Miasto",
    "category": "fair",
    "description": "Traditional Easter fair with crafts and food",
    "free_entry": true,
    "source_url": "https://...",
    "confidence": "confirmed"
  }
]'

# Log a search
python -m weekend_scout log-search \
  --query "imprezy plenerowe Mazowsze marzec 2026" \
  --target-weekend 2026-03-28 \
  --cities '["Warsaw", "Radom", "Lodz"]' \
  --phase broad \
  --result-count 7

# Mark events as served (after Telegram send)
python -m weekend_scout cache-mark-served --date 2026-03-28
```

**Dedup key generation:**

```python
import re

def dedup_key(event_name: str, city: str, start_date: str) -> str:
    name = re.sub(r'[^a-z0-9]', '', event_name.lower())
    city_clean = re.sub(r'[^a-z0-9]', '', city.lower())
    return f"{name}_{city_clean}_{start_date}"
```

This catches obvious duplicates (same event from two sources). The agent
handles fuzzy dedup (slightly different names for the same event) during
its analysis step.

### 4.4 Search Strategy (Agent-Executed)

This is the core logic, executed by the Claude agent following the skill prompt.
The strategy has four phases with a hard budget.

**Budget:** Max 8 searches + max 10 fetches = 18 tool calls ceiling.

#### Phase 1: Cache Check (0 tool calls)

Before any web searching, the agent asks Python for cached events:

```bash
python -m weekend_scout init
```

This returns:
- Config (home city, radius, preferences)
- City list with tiers
- Cached events for next weekend (if any)
- Search log: which searches were already run this week
- Suggested search queries (generated by Python based on config + language)

If the cache already has 10+ confirmed events for next weekend, the agent
can skip straight to ranking and trip building, running only a few verification
fetches.

**The `init` output (JSON):**

```json
{
  "config": {
    "home_city": "Warsaw",
    "radius_km": 150,
    "search_language": "pl",
    "precise_location": "Mokotow, Warsaw",
    "target_weekend": {
      "saturday": "2026-03-28",
      "sunday": "2026-03-29"
    }
  },
  "cities": {
    "tier1": ["Łódź", "Radom", "Lublin"],
    "tier2": ["Płock", "Siedlce", "Kielce", "Piotrków Trybunalski"],
    "tier3": ["Pruszków", "Piaseczno", "Legionowo", "Otwock", "Żyrardów"]
  },
  "cached_events": [
    {
      "event_name": "Jarmark Wielkanocny",
      "city": "Warsaw",
      "start_date": "2026-03-28",
      "confidence": "likely"
    }
  ],
  "searches_this_week": [
    "imprezy plenerowe mazowsze marzec 2026"
  ],
  "suggested_queries": {
    "broad": [
      "imprezy plenerowe weekend 28-29 marca 2026 Mazowsze",
      "festyny jarmarki okolice Warszawy marzec 2026",
      "wydarzenia plenerowe weekend marzec 2026 Polska",
      "outdoor festivals events Poland March 28-29 2026"
    ],
    "targeted": {
      "Łódź": ["Łódź imprezy plenerowe 28-29 marca 2026"],
      "Radom": ["Radom festyn jarmark marzec 2026"],
      "Lublin": ["Lublin wydarzenia weekend 28-29 marca 2026"]
    }
  }
}
```

**Query generation logic in Python (`cities.py` or `queries.py`):**

```python
def generate_broad_queries(config, target_sat, target_sun):
    lang = config["search_language"]
    city = config["home_city"]
    region = get_region_name(city)  # "Mazowsze" for Warsaw

    sat_str = format_date_local(target_sat, lang)  # "28 marca 2026"
    sun_str = format_date_local(target_sun, lang)

    queries = [
        f"imprezy plenerowe weekend {sat_str} {region}",
        f"festyny jarmarki okolice {city} marzec 2026",
        f"wydarzenia plenerowe weekend marzec 2026 Polska",
        f"outdoor festivals events Poland {target_sat.strftime('%B %d-%d')} 2026",
    ]
    return queries


def generate_targeted_queries(tier1_cities, lang, target_sat):
    sat_str = format_date_local(target_sat, lang)
    return {
        city: [f"{city} imprezy plenerowe {sat_str}"]
        for city in tier1_cities
    }
```

#### Phase 2: Broad Sweep (3-5 searches)

The agent runs the suggested broad queries, skipping any already in the search log.

```
WebSearch("imprezy plenerowe weekend 28-29 marca 2026 Mazowsze")
WebSearch("festyny jarmarki okolice Warszawy marzec 2026")
WebSearch("wydarzenia plenerowe weekend marzec 2026 Polska")
WebSearch("outdoor festivals events Poland March 28-29 2026")
```

The agent examines returned titles and URLs. Decision matrix for each result:

| Title pattern                                | Action          |
|----------------------------------------------|-----------------|
| Aggregator listing multiple events           | Queue for fetch |
| Specific event with date + city in title     | Extract what we can, queue fetch if promising |
| Clearly irrelevant (museum, indoor, wrong date) | Skip         |
| City tourism portal "co robić w weekend"     | Queue for fetch |

**Title-only extraction example:**
Title: `"Dni Radomia 2026 - 28-29 marca - Program"` allows the agent to
immediately record: event_name="Dni Radomia", city="Radom",
start_date="2026-03-28", confidence="unverified".

#### Phase 3: Aggregator Deep-Dive (3-8 fetches)

The agent fetches the most promising URLs from Phase 2. Each fetch uses a
targeted extraction prompt:

```
WebFetch(
  url: "https://goout.net/pl/festiwale/warszawa/...",
  prompt: "List ALL outdoor events, festivals, fairs, markets (jarmark),
    city days (Dni Miasta), historical reenactments, food festivals,
    and street events happening between March 28 and March 29, 2026,
    within the area covered by this page.
    For each event, provide:
    1. Event name
    2. City and venue/location
    3. Exact dates and times
    4. Brief description (1 sentence)
    5. Whether entry is free
    Exclude: museums, galleries, theaters, cinemas, indoor concerts,
    recurring weekly markets."
)
```

Haiku returns a structured list. One good aggregator page often yields 5-15 events.

The agent saves all discovered events to cache via:

```bash
python -m weekend_scout save --events '[...]'
```

**Important:** Events for future weekends (not next weekend) also get saved.
They will be served from cache when their weekend comes.

#### Phase 4: Targeted City Searches (2-5 searches, only if needed)

The agent checks which Tier 1 cities are NOT yet covered by Phase 2-3 results.
For each uncovered Tier 1 city, it runs one targeted search:

```
WebSearch("Łódź imprezy plenerowe 28-29 marca 2026")
```

If the title results reveal something promising, fetch one URL per city.

#### Phase 5: Verification Fetches (1-3 fetches)

For the top 3-5 candidate events (the ones likely to make the final
recommendations), the agent fetches the official source page to confirm:

- The event is actually happening (not last year's cached page)
- Dates and times are correct
- Get specific location details for trip planning

```
WebFetch(
  url: "https://radom.pl/dni-radomia-2026",
  prompt: "Is this event confirmed for March 28-29, 2026?
    What are the exact times, location address, and program highlights?
    Is entry free?"
)
```

After verification, the agent updates event confidence to "confirmed".

#### Search Budget Summary

| Phase                | Searches | Fetches | Total |
|----------------------|----------|---------|-------|
| 1. Cache check       | 0        | 0       | 0     |
| 2. Broad sweep       | 3-5      | 0       | 3-5   |
| 3. Aggregator fetch  | 0        | 3-8     | 3-8   |
| 4. Targeted cities   | 2-5      | 0-3     | 2-8   |
| 5. Verification      | 0        | 1-3     | 1-3   |
| **Total**            | **5-10** | **4-14**| **~18**|

As the cache fills over weeks of use, Phases 2-4 shrink. A mature cache
might need only Phase 1 + Phase 5 (verification only), costing 3-5 tool calls.

### 4.5 Scoring and Ranking (Agent-Executed)

The agent scores events using simple, consistent criteria. No ML, no learning
from user behavior. The skill prompt defines the rubric:

**Event Score (1-10):**

| Factor                          | Points   |
|---------------------------------|----------|
| Category match (festival/fair vs. generic) | 0-3 |
| Scale (city-wide event vs. small local) | 0-2 |
| Uniqueness (annual vs. monthly) | 0-2     |
| Confidence level                | 0-1     |
| Free entry                      | 0-1     |
| Source quality (official site vs. aggregator) | 0-1 |

The agent applies this rubric mentally (in-prompt), not via Python code.
No need for a separate `scorer.py`.

**Trip building logic (agent-executed):**

For home city events: pick top 3 by score. Simple list.

For nearby city trips: the agent groups events by geographic proximity
and builds up to 3 trip options:

- **Option A (easy day trip):** Single nearby city, 1-2 events, under 2h drive
- **Option B (full day trip):** 1-2 cities in a loop, multiple events
- **Option C (weekend trip):** Farther city or 2-city loop, overnight possible

For each trip option, the agent includes:
- Ordered list of stops
- Distance between stops (from city list, straight-line)
- Estimated driving time (from heuristic)
- Recommended departure time (back-calculated from event start times)
- Estimated return time

### 4.6 Telegram Sender (`telegram.py`)

**Purpose:** Format and send the final message to a Telegram group/channel.

**Dependencies:** `python-telegram-bot` library or direct `requests` to Bot API.
For MVP, direct `requests` is simpler (no async needed).

**Message format:**

```
Weekend Scout | March 28-29, 2026

IN WARSAW:

1. Jarmark Wielkanocny (Easter Fair)
   Stare Miasto | Sat-Sun 10:00-20:00
   Traditional crafts, food stalls, live folk music
   Free entry
   https://...

2. Warsaw Food Truck Festival
   Pole Mokotowskie | Sat 11:00-22:00
   50+ food trucks, DJ sets, family zone
   Free entry
   https://...

3. Wiosenny Bieg Warszawski (Spring Run)
   Lazienki Park | Sun 9:00-13:00
   Open 5K/10K run through the park
   Registration: 30 PLN
   https://...

ROAD TRIPS:

A. Łódź Day Trip
   Mokotow -> Łódź (131 km, ~1h40)
   Festiwal Czterech Kultur
   ul. Piotrkowska | Sat-Sun all day
   Multicultural festival with food and music
   -> Mokotow (131 km, ~1h40)
   Leave by: 9:00 | Back by: ~20:00

B. Radom + Kielce Loop
   Mokotow -> Radom (92 km, ~1h10)
   Jarmark Radomski | Rynek | Sat 10:00-18:00
   -> Kielce (84 km, ~1h05)
   Kielce Street Food Festival | Sat-Sun
   -> Mokotow (180 km, ~2h15)
   Leave by: 8:30 | Back by: ~21:00

C. Kazimierz Dolny Day Trip
   Mokotow -> Kazimierz Dolny (140 km, ~2h00)
   Festiwal Sztuki | Rynek
   Sat-Sun | Art fair + open-air cinema
   -> Mokotow (140 km, ~2h00)
   Leave by: 8:00 | Back by: ~20:30

---
Scouted by Weekend Scout
```

**Implementation:**

```python
import requests

def send_telegram(config: dict, message: str) -> bool:
    url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage"
    payload = {
        "chat_id": config["telegram_chat_id"],
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    resp = requests.post(url, json=payload)
    return resp.status_code == 200
```

**Message length:** Telegram allows up to 4096 characters per message. If the
message exceeds this, the Python tool splits it into multiple messages
(split at section boundaries, not mid-sentence).

**CLI:**

```bash
python -m weekend_scout send --message "$(cat /tmp/scout_message.txt)"
# or
python -m weekend_scout send --file /tmp/scout_message.txt
```

### 4.7 Scheduling

**MVP:** System cron job. No daemon, no systemd timer.

```cron
# Run every Friday at 18:00
0 18 * * 5 cd ~/weekend-scout && python -m weekend_scout run 2>&1 >> ~/.weekend-scout/scout.log
```

The `run` command:
1. Calls `init` to prepare data
2. Invokes Claude Code with the skill prompt and the init data as context
3. Claude Code runs the search/fetch/rank pipeline
4. Claude Code calls `send` to deliver the message

**For MVP**, the `run` command can simply print instructions for the user to
invoke `/weekend-scout` manually in Claude Code. Full automation (cron calling
Claude Code programmatically) can come later using the Claude Code SDK or
`claude --message` CLI flag.

---

## 5. Claude Code Skill Definition

### 5.1 File Structure

```
~/.claude/skills/weekend-scout/
    SKILL.md
```

### 5.2 SKILL.md

The skill should use 'disable-model-invocation: true' since it has side effects (Telegram sending, web searching). We do not want Claude auto-triggering this when you doing unrelated work in the same project. 

```yaml
---
name: weekend-scout
description: >
  Scout outdoor events, festivals, and fairs happening next weekend
  in your city and nearby cities. Builds trip options and posts to Telegram.
argument-hint: [city] [radius-km]
allowed-tools: Bash, Read, Write, WebSearch, WebFetch
---
```

```markdown
## Weekend Scout

You are a weekend trip scout. Your job is to find interesting outdoor events
happening NEXT weekend (the upcoming Saturday and Sunday) in the user's city
and within driving distance, then build trip options and send them to Telegram.

### Step 1: Initialize

Run the Python tool to load config, city list, cached events, and search suggestions:

\`\`\`bash
cd ~/weekend-scout && python -m weekend_scout init
\`\`\`

If this is the first run, guide the user through setup:
\`\`\`bash
cd ~/weekend-scout && python -m weekend_scout setup
\`\`\`

If the user provided arguments, override:
- First arg: home city
- Second arg: radius in km

Review the init output. Note:
- How many cached events exist for next weekend
- Which cities are Tier 1 (must be covered)
- Which searches were already run this week
- The suggested search queries

### Step 2: Search for Events

Follow this search strategy strictly. Do NOT exceed the budget.

**Budget: max 8 searches + max 10 fetches = 18 tool calls.**

**Phase A - Broad sweep (3-5 searches):**
Run the suggested broad queries from init output. Skip any already in search log.
Queries should be in the local language (from config). Include 1 English query.

After each search, examine titles and URLs:
- If a title reveals a specific event (name + city + date), record it immediately
- If a URL points to an aggregator listing many events, queue it for fetching
- Skip anything clearly irrelevant (museums, indoor events, wrong dates)

**Phase B - Aggregator deep-dive (3-8 fetches):**
Fetch the most promising aggregator URLs. Use this prompt template:

"List ALL outdoor events, festivals, fairs, markets (jarmark), city days
(Dni Miasta), reenactments, food festivals, and street events happening
on [DATES] within the area covered by this page. For each: event name,
city, venue, dates/times, 1-sentence description, free entry or not.
Exclude: museums, galleries, theaters, cinemas, indoor events, weekly markets."

**Phase C - Targeted city searches (only if needed):**
Check which Tier 1 cities have zero events after Phase A+B.
For each uncovered Tier 1 city, run one search in local language.
Fetch only if results look promising.

**Phase D - Verification (1-3 fetches):**
For your top 5 candidate events, fetch the official source to confirm
dates and get details. Update confidence to "confirmed".

After all searching, save ALL discovered events to cache (including events
for future weekends that you noticed along the way):

\`\`\`bash
python -m weekend_scout save --events '<JSON array of events>'
\`\`\`

Log each search:
\`\`\`bash
python -m weekend_scout log-search --query "..." --target-weekend "2026-03-28" \
  --cities '["city1", "city2"]' --phase broad --result-count N
\`\`\`

### Step 3: Score and Rank

Score each event 1-10 using these criteria:
- Category match (festival/fair = high, generic event = low): 0-3
- Scale (city-wide = high, small local = low): 0-2
- Uniqueness (annual event = high, monthly = low): 0-2
- Confidence (confirmed = 1, likely = 0.5, unverified = 0): 0-1
- Free entry: 0-1
- Source quality (official site = 1, aggregator = 0.5): 0-1

Select:
- Top 3 events in the home city
- Up to 3 road trip options from nearby cities

### Step 4: Build Trip Options

For home city: list top 3 events with details.

For road trips, build options using city distances from the init data:
- Option A: Easy day trip (single city, under 2h drive)
- Option B: Full day trip (1-2 cities in a loop)
- Option C: Longer trip (farther city or multi-stop)

For each trip option include:
- Route: Home -> City A (X km, ~Yh) -> [City B] -> Home
- Events at each stop with times
- Recommended departure time (back-calculate from first event)
- Estimated return time
- Use the user's precise_location as the start/end point name

### Step 5: Format and Send

Format the message following this template:

Weekend Scout | [Date Range]

IN [HOME CITY]:

1. [Event Name]
   [Venue] | [Day] [Times]
   [1-line description]
   [Free/Paid]
   [URL]

ROAD TRIPS:

A. [Trip Name]
   [Start] -> [City] ([distance], ~[time])
   [Event details]
   -> [next stop or home]
   Leave by: [time] | Back by: ~[time]

---
Scouted by Weekend Scout

Send via Python:
\`\`\`bash
python -m weekend_scout send --file /tmp/scout_message.txt
\`\`\`

If no Telegram is configured, just display the message.

### Step 6: Report

Tell the user:
- How many events were found
- How many are new (not in cache before)
- How many searches/fetches were used (vs budget)
- Any Tier 1 cities with zero coverage (flag for next time)

### What counts as a good event

INCLUDE:
- Open-air festivals (music, food, craft, cultural)
- City Days (Dni Miasta), town celebrations
- Large fairs and markets (jarmark, kiermasz, fair)
- Historical reenactments, outdoor spectacles
- Street art and performer festivals
- Food truck rallies, beer festivals, wine festivals
- Outdoor concerts, open-air cinema
- Large sporting events with public attendance

EXCLUDE:
- Museum openings, gallery exhibitions
- Indoor theater, cinema, opera, conferences
- Small recurring weekly farmers markets
- Private corporate events
- Ticketed indoor concerts
- Religious services (but religious festivals/processions are OK)
```

---

## 6. Project File Structure

```
~/Weekend-Ccout/
    .claude/
    pyproject.toml
    README.md
    weekend_scout/
        __init__.py
        __main__.py          # CLI entry point (argparse)
        config.py            # YAML config read/write/setup
        cities.py            # City list generation + tiers + queries
        cache.py             # SQLite operations
        distance.py          # Haversine + drive time heuristic
        telegram.py          # Message sending
    data/
        cities15000.txt      # GeoNames data file (downloaded once)
        regions.json         # Mapping: city -> region name (for queries)
    tests/
        test_cities.py
        test_cache.py
        test_distance.py
```

**Dependencies (pyproject.toml):**

```toml
[project]
name = "weekend-scout"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pyyaml",
    "requests",
]

[project.scripts]
weekend-scout = "weekend_scout.__main__:main"
```

Only two external dependencies: `pyyaml` for config, `requests` for Telegram API.
SQLite is built into Python. No search APIs, no routing APIs, no LLM libraries.

---

## 7. MVP Implementation Plan

Each step produces something testable before moving to the next.

**Step 1: Project skeleton + config (day 1)**
- Set up pyproject.toml, directory structure
- Implement `config.py`: setup wizard, read/write YAML
- Test: `python -m weekend_scout setup` creates config file

**Step 2: City list (day 1)**
- Download GeoNames cities15000.txt
- Implement `cities.py`: parse GeoNames, filter by distance, assign tiers
- Implement `distance.py`: Haversine + drive time heuristic
- Create `regions.json` mapping for Poland (can be small, ~20 entries)
- Test: `python -m weekend_scout init` outputs city list with tiers

**Step 3: Cache (day 2)**
- Implement `cache.py`: create DB, save events, query by date, log searches
- Implement dedup key logic
- Test: save and retrieve test events

**Step 4: Query generation (day 2)**
- Add query generation to `cities.py` (broad + targeted)
- Test: `init` command returns suggested queries for next weekend

**Step 5: Telegram sender (day 2)**
- Implement `telegram.py`: format message, send, handle message splitting
- Test: send a test message to your group

**Step 6: Claude Code skill (day 3)**
- Write SKILL.md and install to `~/.claude/skills/weekend-scout/`
- Test: run `/weekend-scout` in Claude Code
- Iterate on the skill prompt based on agent behavior
- First real scouting run

**Step 7: Polish and iterate (day 3+)**
- Tune search queries based on actual result quality
- Adjust scoring rubric
- Add region mappings for cities outside Mazowsze
- Test with different radius values

**Total estimated effort: 3-4 days to working MVP.**

---

## 8. Example: Full Run Walkthrough

User types `/weekend-scout` in Claude Code on Thursday evening.

**1. Agent runs `init`:**

```
$ python -m weekend_scout init
{
  "config": { "home_city": "Warsaw", "radius_km": 150, ... },
  "cities": {
    "tier1": ["Łódź", "Radom", "Lublin"],
    "tier2": ["Płock", "Siedlce", "Kielce", ...],
    ...
  },
  "cached_events": [],
  "searches_this_week": [],
  "suggested_queries": { ... }
}
```

No cached events, first run. Agent proceeds to search.

**2. Phase A - Broad sweep:**

```
WebSearch("imprezy plenerowe weekend 28-29 marca 2026 Mazowsze")
-> 8 results, including:
   - "Jarmarki i festyny w Warszawie - marzec 2026 | GoOut.net"  [FETCH]
   - "Dni Radomia 2026 - 28-29 marca - Program"  [TITLE EXTRACT]
   - "Muzeum Narodowe - nowa wystawa marzec 2026"  [SKIP - museum]

WebSearch("festyny jarmarki okolice Warszawy marzec 2026")
-> 6 results, including:
   - "Festyny i wydarzenia - Mazovia region | AllEvents"  [FETCH]
   - "Wiosenny Jarmark Rzemiosla - Kazimierz Dolny"  [TITLE EXTRACT]

WebSearch("outdoor festivals events Poland March 28-29 2026")
-> 7 results, including:
   - "Poland Events March 2026 | VisitPoland.com"  [FETCH]
```

3 searches used. Agent extracted 2 events from titles, queued 3 URLs for fetch.

**3. Phase B - Aggregator fetch:**

```
WebFetch("https://goout.net/...",
  prompt: "List all outdoor events...")
-> Returns 8 events in Warsaw area for the weekend

WebFetch("https://allevents.in/...",
  prompt: "List all outdoor events...")
-> Returns 5 events across Mazowsze

WebFetch("https://visitpoland.com/...",
  prompt: "List all outdoor events...")
-> Returns 3 events (overlap with above)
```

3 fetches used. Agent now has ~16 raw events (with some duplicates).

Agent saves all events to cache, including a June festival it noticed:
```
$ python -m weekend_scout save --events '[...16 events...]'
Saved 14 events (2 duplicates skipped)
```

**4. Phase C - Targeted:**

Łódź has no events yet. Lublin has none.

```
WebSearch("Łódź imprezy plenerowe 28-29 marca 2026")
-> "Festiwal Łódź Czterech Kultur - 28 marca" [TITLE EXTRACT + FETCH]

WebSearch("Lublin wydarzenia weekend 28-29 marca 2026")
-> Nothing relevant for this weekend. OK.
```

2 searches + 1 fetch. Łódź now covered. Lublin has nothing, that is fine.

**5. Phase D - Verification:**

Agent picks top 5 candidates. 2 of them already have official source URLs.

```
WebFetch("https://radom.pl/dni-radomia-2026", "Confirm dates and times...")
-> Confirmed: March 28-29, 10:00-22:00, free entry

WebFetch("https://festival.lodz.pl/...", "Confirm dates and program...")
-> Confirmed: March 28 only, 12:00-23:00, free entry
```

2 fetches. Total tool calls: 3+3+2+1+2 = 11. Well within budget.

**6. Agent scores, ranks, builds trip options, formats message.**

**7. Agent sends:**

```
$ python -m weekend_scout send --file /tmp/scout_message.txt
Message sent to Telegram group.
```

**8. Agent reports:**

"Found 14 events across 6 cities. 3 events in Warsaw, 11 in nearby cities.
Used 5 searches and 6 fetches (11/18 budget). Lublin had no outdoor events
this weekend. All top picks are confirmed. Message sent to Telegram."

---

## 9. Open Decisions (Not Blocking MVP)

These can be resolved after the first few real runs:

1. **Region mapping completeness.** The `regions.json` file needs entries
   for major Polish regions. Start with Mazowsze, add others as users
   change home cities.

2. **Query language for cross-border cities.** When searching for events in
   German cities near Wroclaw, the agent should use German queries. The skill
   prompt should instruct the agent to use the target city's country language.

3. **Cache expiry.** How long to keep old events? A simple rule: delete events
   older than 30 days. Run cleanup on each `init`.

4. **Rate of "no events" results.** If the agent consistently finds nothing for
   small cities, consider dropping Tier 3 entirely and relying only on
   regional queries.

5. **Telegram formatting polish.** The exact message format will evolve based
   on how it reads in the actual Telegram group. Emoji, bold, link formatting
   can be tuned iteratively.
