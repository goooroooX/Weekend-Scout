# Delivery And Audit

Use this reference for Step 5 and Step 6. It defines the exact formatting,
sending, `run_complete`, and final audit contract.

## Format-message contract

`format-message` must receive:

- `city-events`: a JSON array of event dicts
- `trips`: a JSON array of trip dicts

`city-events` payload contract:

```text
event_name, location_name, start_date
optional: end_date, time_info, description, source_url, free_entry
```

`trips` payload contract:

```text
name, route, events, timing
optional: url
```

`city-events` example:

```json
[
  {
    "event_name": "Spring Festival",
    "location_name": "Main Square",
    "start_date": "2026-04-04",
    "time_info": "10:00-18:00",
    "description": "Outdoor city festival.",
    "source_url": "https://example.com/event",
    "free_entry": true
  }
]
```

`trips` example:

```json
[
  {
    "name": "Lodz Day Trip",
    "route": "Warsaw -> Lodz (130 km, ~1h45) -> Warsaw",
    "events": "Spring Fair | Main Square | Sat-Sun all day",
    "timing": "Leave by: 10:00 | Back by: ~20:00",
    "url": "https://example.com/event"
  }
]
```

The `format-message` response returns:

- `written`: HTML file path for Telegram sending
- `preview`: plain-text digest preview for showing in the conversation

Always display the `preview` to the user. Do **not** read the written HTML file back into the conversation.

## Format and send

Before writing JSON payloads, read `references/platform-codex.md`.
Use fresh `_tmp_*.tmp` transport filenames only, for example `_tmp_city_events.tmp` and `_tmp_trips.tmp`.
Write the selected home-city event array to `city_events_json_path` and the selected trip array to `trips_json_path`, then run:

```bash
python -m weekend_scout format-message \
  --saturday "<saturday>" --sunday "<sunday>" \
  --city-events-file "$city_events_json_path" \
  --trips-file "$trips_json_path" \
  --run-id "<run_id>" \
  [--low-results true]

python -m weekend_scout send --file "<path from written>" --run-id "<run_id>"
```

Use `--low-results true` when `total_events < 3`.

Expected response shape:

```json
{
  "written": "D:\\Work\\Weekend-Scout\\.weekend_scout\\cache\\scout_message.txt",
  "preview": "Weekend Scout | April 4-5, 2026\n..."
}
```

## Send handling

If `{"sent": true}`:

- tell the user the digest was sent to Telegram
- proceed to served marking

If `{"sent": false}` because Telegram is not configured:

- do **not** mark served
- tell the user:

```text
python -m weekend_scout config telegram_bot_token YOUR_BOT_TOKEN
python -m weekend_scout config telegram_chat_id YOUR_CHAT_ID
```

If `{"sent": false}` because Telegram sending failed:

- do **not** mark served
- report the failure
- suggest checking the configured token and chat ID

## Mark served

If send succeeds:

```bash
python -m weekend_scout cache-mark-served --date "<saturday>"
```

Here, `saturday` means the ISO Saturday date from `init-skill`
(`output.config.target_weekend.saturday`), for example `2026-04-04`.

Set:

- `served_marked = true`
- `send_reason = "sent"`

If send failed because Telegram is not configured:

- `served_marked = false`
- `send_reason = "telegram_not_configured"`

If send failed because Telegram sending failed:

- `served_marked = false`
- `send_reason = "send_failed"`

## Run-complete contract

After the send/no-send outcome is known, always log `run_complete`.

`events_sent` means the number of items selected for the digest:

```text
events_sent = len(city_events_selected) + len(trip_options)
```

It does **not** become zero just because Telegram was unconfigured. Delivery state is represented by
`sent`, `send_reason`, and `served_marked`.

Before writing the uncovered-tier1 payload, read `references/platform-codex.md`, write the uncovered tier1 array to a fresh `_tmp_uncovered_tier1.tmp` file, then run:

```bash
python -m weekend_scout run-complete --run-id "<run_id>" \
  --target-weekend "<saturday>" \
  --events-sent <city_count + trip_count> \
  --sent <true|false> \
  --send-reason <sent|telegram_not_configured|send_failed> \
  --served-marked <true|false> \
  --uncovered-tier1-file "$uncovered_tier1_path"
```

## Audit gate

After `run_complete`, always run:

```bash
python -m weekend_scout audit-run --run-id "<run_id>"
```

`audit-run` is debug-only by default. It should not block the normal user summary.

## Final user report

Always report first:

- how many events were found and how many were new vs cached
- budget used: `searches_used/max_searches`, `fetches_used/max_fetches`
- any cities with zero coverage, especially tier1 cities
- the normal digest preview

If `total_events < 3`, also tell the user:

```text
python -m weekend_scout config max_searches NN
python -m weekend_scout config max_fetches NN
```

If the audit returns `ok: false`, append:

```text
DEBUG INFORMATION
```

Then summarize the audit mismatches briefly. Do **not** tell the user to fix the skill, switch modes, or perform maintenance.
