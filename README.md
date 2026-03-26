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
```

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
| `init` | Load config + cities + cache for a scout run (JSON output) |
| `save --events '<JSON>'` | Save discovered events to cache |
| `send --message '<text>'` | Send formatted message to Telegram |
| `send --file <path>` | Send message from file to Telegram |
| `cache-query --date YYYY-MM-DD` | Query cached events for a weekend |
| `log-search` | Log a completed search to the search log |
| `cache-mark-served --date YYYY-MM-DD` | Mark events as sent to Telegram |
| `run` | Full automated run (init + scout + send) |

## Configuration

Config lives at:
- **Linux/Mac:** `~/.config/weekend-scout/config.yaml`
- **Windows:** `%APPDATA%\weekend-scout\config.yaml`

Run the setup wizard on first use:

```bash
python -m weekend_scout setup
```

## Design

See [docs/weekend-scout-mvp-design.md](docs/weekend-scout-mvp-design.md) for the
full architecture and design decisions.

## License

MIT
