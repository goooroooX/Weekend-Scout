# Weekend Scout — Installation Guide

## Prerequisites

- Python 3.10 or later
- At least one of: Claude Code, OpenAI Codex, or OpenClaw

## One-Liner Install

```bash
git clone https://github.com/goooroooX/Weekend-Scout.git
cd Weekend-Scout
python install/install_skill.py --with-pip
```

This command:
1. Installs the `weekend_scout` Python package (via pip)
2. Copies the skill to your global skill directory (auto-detects platform)
3. Pre-downloads GeoNames city data to the cache

---

## Claude Code (recommended)

### Project-scoped install (already in the repo)

If you cloned the repo into a project you work in, the skill is already available
at `.claude/skills/weekend-scout/SKILL.md`. Claude Code discovers it automatically.

### Global install

```bash
pip install .
python install/install_skill.py --platform claude-code
```

The skill is installed to `~/.claude/skills/weekend-scout/SKILL.md`.

### Verifying

Open Claude Code and type `/weekend-scout`. You should see the skill in the
command palette (or it loads immediately).

### Using

```
/weekend-scout
/weekend-scout Warsaw 200
/weekend-scout --cached-only
```

---

## OpenAI Codex

### Install

```bash
pip install .
python install/install_skill.py --platform codex
```

Files installed to `~/.agents/skills/weekend-scout/`:
- `SKILL.md` — skill instructions
- `agents/openai.yaml` — Codex-specific metadata (disables implicit invocation)

### Verifying

In Codex, type `$weekend-scout` or open the `/skills` menu and look for Weekend Scout.

### Using

```
$weekend-scout
$weekend-scout Berlin 150
```

---

## OpenClaw

### Install

```bash
pip install .
python install/install_skill.py --platform openclaw
```

Files installed to `~/.openclaw/skills/weekend-scout/SKILL.md`.

### Verifying

Start or restart your OpenClaw session. Type `weekend-scout` or check the available
skills list.

---

## Install All Platforms

```bash
python install/install_skill.py --platform all --with-pip
```

---

## Manual Installation

If you prefer to install manually, copy the SKILL.md from the appropriate directory:

| Platform   | Source in repo                           | Destination                          |
|------------|------------------------------------------|--------------------------------------|
| Claude Code | `.claude/skills/weekend-scout/`         | `~/.claude/skills/weekend-scout/`    |
| Codex       | `.agents/skills/weekend-scout/`         | `~/.agents/skills/weekend-scout/`    |
| OpenClaw    | `.openclaw/skills/weekend-scout/`       | `~/.openclaw/skills/weekend-scout/`  |

For Codex, also copy `agents/openai.yaml` into the destination directory.
The OpenClaw repo copy is a generated artifact for packaging/staging in this repo; the
supported installed location remains `~/.openclaw/skills/weekend-scout/`.

---

## Updating

**Users** — re-clone and re-run the installer (same as initial install):

```bash
git clone https://github.com/goooroooX/Weekend-Scout.git
cd Weekend-Scout
python install/install_skill.py --with-pip
```

**Developers** — pull and reinstall:

```bash
git pull
pip install -e ".[dev]"
python skill_template/generate.py   # only if template was changed
```

---

## Uninstalling

Remove the skill directory:

```bash
# Claude Code
rm -rf ~/.claude/skills/weekend-scout

# Codex
rm -rf ~/.agents/skills/weekend-scout

# OpenClaw
rm -rf ~/.openclaw/skills/weekend-scout
```

Uninstall the Python package:

```bash
pip uninstall weekend-scout
```

---

## Configuration

After installation, Weekend Scout will guide you through a one-time setup the first
time you invoke it. You can also configure it directly:

```bash
python -m weekend_scout config telegram_bot_token YOUR_BOT_TOKEN
python -m weekend_scout config telegram_chat_id YOUR_CHAT_ID
```

See the main [README](../README.md) for full configuration options.
