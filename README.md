# Weekend Scout

A Python CLI + Agent Skill that discovers outdoor events, festivals, and
fairs happening next weekend near your city. Builds curated trip options
and delivers them to Telegram.

## Supported Platforms

- **Claude Code** — fully tested, primary development platform
- **OpenAI Codex** — skill compatible, generated from shared template
- **OpenClaw** — skill compatible, generated from shared template
- Any agent supporting the Agent Skills standard (agentskills.io)

## Installation

### For users

```bash
git clone https://github.com/goooroooX/Weekend-Scout.git
cd Weekend-Scout
python install/install_skill.py --with-pip
cd ..
```

The package is now installed system-wide. You can safely delete the
`Weekend-Scout/` folder after installation.

If you already have the package installed and only need to update the skill file:

```bash
python -m weekend_scout install-skill
```

### For developers

```bash
git clone https://github.com/goooroooX/Weekend-Scout.git
cd Weekend-Scout
pip install -e ".[dev]"
```

The skill loads from `.claude/skills/` inside the repo (project-scoped).
Do **not** delete this folder — editable mode links to it.

### Updating

```bash
# Users: re-clone and re-run the installer
git clone https://github.com/goooroooX/Weekend-Scout.git
cd Weekend-Scout
python install/install_skill.py --with-pip

# Developers: pull in your existing clone
git pull
pip install -e ".[dev]"
```

### Uninstalling

```bash
pip uninstall weekend-scout
```

Then delete the skill folder for your platform:
- Claude Code: `~/.claude/skills/weekend-scout/`
- Codex: `~/.codex/skills/weekend-scout/`
- OpenClaw: `~/.openclaw/skills/weekend-scout/`

### Quick Start (after install)

```
/weekend-scout            # Claude Code
$weekend-scout            # Codex
weekend-scout             # OpenClaw
```

See [install/README.md](install/README.md) for the full installation guide.

## How It Works

Weekend Scout has two parts:

1. **Python CLI** (`weekend_scout/`) — handles config, city data, caching,
   distance calculations, and Telegram delivery
2. **Agent Skill** (SKILL.md) — instructs the AI agent to search for events,
   extract and score them, build trip options, and format output

The skill calls the CLI for data operations and uses the agent's built-in
web search/fetch tools for event discovery.

GeoNames city data (used for geocoding and nearby city discovery) is
downloaded automatically on first run to the platform cache directory.

## Telegram Setup

Weekend Scout can send event summaries to a Telegram chat (group, channel, or DM).
This is optional — if Telegram is not configured the skill prints the digest in chat
and shows the commands to enable delivery.

### Step 1: Create a bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`, choose a name and username (e.g. `weekend_scout_bot`)
3. BotFather replies with your **bot token** — looks like `123456789:ABCdefGhIJK...`

### Step 2: Get your chat ID

**For a group:** add the bot, send a message, then open:
```
https://api.telegram.org/bot<TOKEN>/getUpdates
```
Look for `"chat":{"id":-100XXXXXXXXXX}` (negative number = group/channel).

**For a DM:** open a chat with your bot, send `/start`, then use the same URL.
Your chat ID is the positive number in `"chat":{"id":XXXXXXXXX}`.

### Step 3: Configure Weekend Scout

```bash
python -m weekend_scout config telegram_bot_token "YOUR_BOT_TOKEN"
python -m weekend_scout config telegram_chat_id "YOUR_CHAT_ID"
```

## Usage

### Via skill

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
| `setup` | Interactive setup wizard |
| `setup --json '{...}'` | Apply a JSON config payload (no prompts) |
| `find-city --name CITY` | Look up a city in GeoNames |
| `config` | Show current configuration as JSON |
| `config KEY VALUE` | Set a single configuration value |
| `init [--city CITY] [--radius KM]` | Load config + city list + cache (JSON output) |
| `save --events '<JSON>'` | Save discovered events to cache |
| `format-message` | Format the scout digest and write to file |
| `send --file <path>` | Send a formatted message file to Telegram |
| `send --message '<text>'` | Send a text message to Telegram |
| `cache-query --date YYYY-MM-DD` | Query cached events for a weekend |
| `log-search` | Log a completed web search |
| `log-action` | Append a structured action log entry |
| `cache-mark-served --date YYYY-MM-DD` | Mark events as sent |
| `install-skill [--platform P]` | Copy bundled SKILL.md to global skills directory |
| `download-data` | Download GeoNames cities15000 to cache dir |

## Configuration

Config lives at:
- **Linux/Mac:** `~/.config/weekend-scout/config.yaml`
- **Windows:** `%LOCALAPPDATA%\weekend-scout\config.yaml`

| Key | Default | Description |
|-----|---------|-------------|
| `home_city` | `""` | Home city — set automatically on first run |
| `home_country` | `""` | Country name — auto-detected from GeoNames |
| `home_coordinates` | `{lat:0, lon:0}` | Lat/lon — auto-set from GeoNames |
| `radius_km` | `150` | Search radius in km |
| `search_language` | `"en"` | Language code for queries |
| `telegram_bot_token` | `""` | Telegram bot token |
| `telegram_chat_id` | `""` | Telegram chat/group/channel ID |

## Supported Countries

27 countries with native-language search queries:
Poland, Germany, France, Czech Republic, Slovakia, Austria, Hungary, Ukraine,
Lithuania, Latvia, Estonia, Belarus, Italy, Spain, Portugal, Netherlands, Sweden,
Norway, Denmark, Finland, Romania, Croatia, Bulgaria, Serbia, Greece, Turkey, Russia.

English-language queries are used as a fallback for any other location.

## Project Structure

```
Weekend-Scout/
    weekend_scout/           Python package (CLI + data layer)
    skill_template/          Skill template + generator (source of truth)
    .claude/skills/          Generated skill for Claude Code
    .codex/skills/           Generated skill for Codex
    .openclaw/skills/        Generated skill for OpenClaw
    install/                 Cross-platform installer
    tests/                   Test suite
    docs/                    Design docs, backlog, references
```

## For Developers

### Skill Template System

Skills are generated from a single template using a preprocessor.
After editing `skill_template/weekend-scout.template.md`:

```bash
python skill_template/generate.py
```

This regenerates all platform SKILL.md files. See
[skill_template/README.md](skill_template/README.md) for details.

### Development Setup

```bash
git clone https://github.com/goooroooX/Weekend-Scout.git
cd Weekend-Scout
pip install -e ".[dev]"       # editable install with test deps
python -m pytest tests/ -v
```

Or use the installer with the `--dev` flag:

```bash
python install/install_skill.py --with-pip --dev
```

## Design

See [docs/weekend-scout-mvp-design.md](docs/weekend-scout-mvp-design.md)
for architecture and design decisions.

## License

MIT
