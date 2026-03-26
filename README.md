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

## Quick Start

```bash
# 1. Run the setup wizard (location, radius, language, Telegram)
python -m weekend_scout setup

# 2. Set up Telegram (see below) or skip to use CLI-only mode

# 3. Run the skill in Claude Code
/weekend-scout
```

## Telegram Setup

Weekend Scout can send event summaries to a Telegram chat (group, channel, or DM).
This is optional -- the skill works without it, printing results in Claude Code instead.

### Step 1: Create a bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a display name (e.g. "Weekend Scout")
4. Choose a username ending in `bot` (e.g. `weekend_scout_bot`)
5. BotFather replies with your **bot token** -- looks like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyz`

### Step 2: Get your chat ID

**For a group chat:**

1. Add the bot to your Telegram group
2. Send `/start` in the group
3. Open this URL in a browser (replace `<TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
4. Find `"chat":{"id":-100XXXXXXXXXX}` in the JSON -- that negative number is your chat ID

**For a direct message:**

1. Open a chat with your bot and send `/start`
2. Open the same `getUpdates` URL
3. Your chat ID is the positive number in `"chat":{"id":XXXXXXXXX}`

**For a channel:**

1. Add the bot as a **channel administrator** (bots need admin rights to post in channels)
2. Post any message in the channel
3. Use the `getUpdates` URL to find the channel's chat ID

> **Tip:** `getUpdates` only shows recent messages. If you see an empty `result`,
> make sure the bot is a group member and send a new `/start` message, then retry.

### Step 3: Configure Weekend Scout

```bash
python -m weekend_scout config telegram_bot_token "YOUR_BOT_TOKEN"
python -m weekend_scout config telegram_chat_id "YOUR_CHAT_ID"
```

### Step 4: Test it

```bash
python -m weekend_scout send --message "Hello from Weekend Scout!"
```

You should see `{"sent": true}` and the message appear in your Telegram chat.
If you see `{"sent": false}`, check:

- Is the bot token correct? (no extra spaces)
- Is the bot a member of the group?
- Is the chat ID correct? (include the `-` for groups/channels)

### Verify your config

```bash
python -m weekend_scout config
```

This prints your full configuration as JSON, including `telegram_bot_token` and `telegram_chat_id`.

## Usage

### Via Claude Code skill

```
/weekend-scout
/weekend-scout Krakow 120
```

### Via CLI

```bash
python -m weekend_scout --help
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `setup` | Interactive first-run setup wizard |
| `config` | Show current configuration |
| `config KEY VALUE` | Set a single configuration value |
| `init` | Load config + cities + cache for a scout run (JSON output) |
| `save --events '<JSON>'` | Save discovered events to cache |
| `send --message '<text>'` | Send formatted message to Telegram |
| `send --file <path>` | Send message from file to Telegram |
| `cache-query --date YYYY-MM-DD` | Query cached events for a weekend |
| `log-search` | Log a completed search to the search log |
| `cache-mark-served --date YYYY-MM-DD` | Mark events as sent to Telegram |
| `download-data` | Download GeoNames city data |
| `run` | Full automated run (init + scout + send) |

## Configuration

Config lives at:
- **Linux/Mac:** `~/.config/weekend-scout/config.yaml`
- **Windows:** `%APPDATA%\weekend-scout\config.yaml`

Set individual values:

```bash
python -m weekend_scout config home_city Warsaw
python -m weekend_scout config radius_km 200
python -m weekend_scout config telegram_bot_token "123456789:ABC..."
```

Or run the full setup wizard:

```bash
python -m weekend_scout setup
```

## Design

See [docs/weekend-scout-mvp-design.md](docs/weekend-scout-mvp-design.md) for the
full architecture and design decisions.

## License

MIT
