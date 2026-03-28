# Weekend Scout

Weekend Scout is a Claude Code skill + Python CLI that discovers outdoor events,
festivals, and fairs happening next weekend in your city and within driving distance.
It builds curated trip options and delivers them to a Telegram group.

## Prerequisites

- Python 3.10+
- Claude Code with Pro or Max subscription (for WebSearch/WebFetch tools)

## Installation

```bash
pip install -e ".[dev]"
python -m weekend_scout download-data
```

`download-data` fetches the GeoNames city database (~50 MB) used for distance
calculations and auto-detecting your city's coordinates and language.

## Quick Start

```bash
# Install (see above), then in Claude Code:
/weekend-scout
```

On first run the skill will ask for your city and search radius, resolve coordinates
automatically, and proceed straight to scouting. No manual setup step needed.

To configure Telegram delivery (optional), see the **Telegram Setup** section below.

## Telegram Setup

Weekend Scout can send event summaries to a Telegram chat (group, channel, or DM).
This is optional — if Telegram is not configured the skill prints the digest directly
in Claude Code and shows the commands to enable delivery.

### Step 1: Create a bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a display name (e.g. "Weekend Scout")
4. Choose a username ending in `bot` (e.g. `weekend_scout_bot`)
5. BotFather replies with your **bot token** — looks like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyz`

### Step 2: Disable privacy mode (required for groups)

By default Telegram bots only see commands (e.g. `/start`), not regular messages.
To allow `getUpdates` to capture your group messages:

1. In @BotFather, send `/setprivacy`
2. Select your bot
3. Choose **Disable**

This only affects what the bot *reads* — it has no impact on sending messages.

### Step 3: Get your chat ID

**For a group chat:**

1. Add the bot to your Telegram group
2. Send any message in the group (e.g. "hello")
3. Open this URL in a browser (replace `<TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
4. Find `"chat":{"id":-100XXXXXXXXXX}` in the JSON — that negative number is your chat ID

**For a direct message:**

1. Open a chat with your bot and send `/start`
2. Open the same `getUpdates` URL
3. Your chat ID is the positive number in `"chat":{"id":XXXXXXXXX}`

**For a channel:**

1. Add the bot as a **channel administrator** (bots need admin rights to post in channels)
2. Post any message in the channel
3. Use the `getUpdates` URL to find the channel's chat ID

> **Tip:** `getUpdates` only shows recent messages. If you see an empty `result`,
> make sure the bot is a group member, send a new message, then retry.

### Step 4: Configure Weekend Scout

```bash
python -m weekend_scout config telegram_bot_token "YOUR_BOT_TOKEN"
python -m weekend_scout config telegram_chat_id "YOUR_CHAT_ID"
```

### Step 5: Test it

```bash
python -m weekend_scout send --message "Hello from Weekend Scout!"
```

You should see `{"sent": true}` and the message appear in your Telegram chat.
If you see `{"sent": false}`, check:

- Is the bot token correct? (no extra spaces)
- Is the bot a member of the group?
- Is the chat ID correct? (include the `-` for groups/channels)

## Usage

### Via Claude Code skill

```
/weekend-scout
/weekend-scout Berlin 100
/weekend-scout --cached-only
```

| Argument | Description |
|----------|-------------|
| `CITY` | Override home city for this run |
| `RADIUS` | Override search radius in km |
| `--cached-only` | Skip web searching; format and send from cached events only |

### Via CLI

```bash
python -m weekend_scout --help
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `setup` | Interactive setup wizard — asks for city and radius, auto-detects everything else |
| `setup --json '{...}'` | Apply a JSON config payload directly (no prompts) |
| `find-city --name CITY` | Look up a city in GeoNames; returns name, country, coordinates, language |
| `config` | Show current configuration as JSON |
| `config KEY VALUE` | Set a single configuration value |
| `init [--city CITY] [--radius KM]` | Load config + city list + cache for a scout run (JSON output) |
| `save --events '<JSON>'` | Save discovered events to cache |
| `format-message` | Format the scout digest and write it to a file |
| `send --file <path>` | Send a formatted message file to Telegram |
| `send --message '<text>'` | Send a text message to Telegram |
| `cache-query --date YYYY-MM-DD` | Query cached events for the weekend containing the given date |
| `log-search` | Log a completed web search to the search log |
| `log-action` | Append a structured action log entry to `action_log.jsonl` |
| `cache-mark-served --date YYYY-MM-DD` | Mark all events for a weekend as sent |
| `download-data` | Download the GeoNames cities15000 database into `data/` |
| `run` | Print instructions for a manual `/weekend-scout` run |

## Configuration

Config lives at:
- **Linux/Mac:** `~/.config/weekend-scout/config.yaml`
- **Windows:** `%LOCALAPPDATA%\weekend-scout\config.yaml`

### Config reference

| Key | Default | Description |
|-----|---------|-------------|
| `home_city` | `""` | Your home city name — set automatically during first run |
| `home_country` | `""` | Country name — auto-detected from GeoNames during setup |
| `home_coordinates` | `{lat:0, lon:0}` | Lat/lon for distance calculations — auto-set from GeoNames; update manually only if the detected point is wrong |
| `radius_km` | `150` | Search radius in km |
| `search_language` | `"en"` | 2-letter language code for queries — auto-derived from country during setup |
| `telegram_bot_token` | `""` | Telegram bot token |
| `telegram_chat_id` | `""` | Telegram chat/group/channel ID |

### Override individual values

```bash
python -m weekend_scout config radius_km 200
python -m weekend_scout config telegram_bot_token "123456789:ABC..."
python -m weekend_scout config telegram_chat_id "-1001234567890"
```

To re-run the setup wizard (city + radius only; re-geocodes automatically):

```bash
python -m weekend_scout setup
```

## Supported countries

27 countries with native-language search queries:
Poland, Germany, France, Czech Republic, Slovakia, Austria, Hungary, Ukraine,
Lithuania, Latvia, Estonia, Belarus, Italy, Spain, Portugal, Netherlands, Sweden,
Norway, Denmark, Finland, Romania, Croatia, Bulgaria, Serbia, Greece, Turkey, Russia.

English-language queries are used as a fallback for any other location.

## Design

See [docs/weekend-scout-mvp-design.md](docs/weekend-scout-mvp-design.md) for the
full architecture and design decisions.

## License

MIT
