# Drewgent Agent ☤

> **Drewgent** is a fork of [Hermes-Agent](https://github.com/NousResearch/hermes-agent) by Nous Research, customized for personal use by [HUMANERD](https://humanerd.ai). This fork adds brain-governed behavior, knowledge persistence, and a feedback loop — while remaining a drop-in replacement for Hermes-Agent.

<p align="center">
  <a href="https://github.com/adm-humanerd/drewgent"><img src="https://img.shields.io/badge/GitHub-adm--humanerd/drewgent-orange?style=for-the-badge" alt="GitHub"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/adm-humanerd/drewgent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
</p>

---

## What is this fork?

Hermes-Agent runs everywhere. Drewgent runs **your way** — from the LLM provider you choose to the colors you see at boot.

This repo is a **fully forkable, self-contained** Drewgent setup. Clone it, configure your provider and skin, run it. No account required.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/adm-humanerd/drewgent.git
cd drewgent

# 2. Install
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[all]"

# 3. Configure — pick your provider below
cp .env.example .env
# Edit .env and add your API key

# 4. Run
drewgent
```

That's it. See [Configuration](#configuration) below to set your provider and skin.

---

## Configuration

All config is in `~/.drewgent/config.yaml` (created on first run via `drewgent setup`) and `~/.drewgent/.env` (API keys only).

### LLM Provider Setup

Edit `~/.drewgent/.env` and uncomment the provider you want. **Only one is needed.**

```bash
# ── Pick one ──────────────────────────────────────────────

# MiniMax (default for this fork)
MINIMAX_API_KEY=your_key_here

# OpenRouter (access to 200+ models via OpenAI-compatible API)
OPENROUTER_API_KEY=your_key_here

# Google Gemini
GOOGLE_API_KEY=your_key_here

# Z.ai / Zhipu GLM
GLM_API_KEY=your_key_here

# Kimi / Moonshot
KIMI_API_KEY=your_key_here

# OpenCode Zen (curated models, pay-as-you-go)
OPENCODE_ZEN_API_KEY=your_key_here

# Hugging Face (routes to 20+ open models)
HF_TOKEN=your_token_here
```

After adding your key, switch to it:

```bash
drewgent model          # interactive model picker
# Or: drewgent setup    # full setup wizard
```

The agent uses whatever provider you configured. No code changes needed.

### Skin / Theme Setup

The CLI boots with a banner and animated spinner. All of it is customizable via YAML skins.

**Option A — Use a built-in skin:**

Edit `~/.drewgent/config.yaml`:

```yaml
display:
  skin: ares      # alternatives: default, mono, slate, ares
```

```bash
# Or change at runtime
drewgent            # then type: /skin ares
```

**Option B — Create your own skin:**

```bash
mkdir -p ~/.drewgent/skins
```

Create `~/.drewgent/skins/mydesign.yaml`:

```yaml
name: mydesign
description: My custom Drewgent skin

colors:
  banner_border: "#4169E1"
  banner_title: "#FFD700"
  banner_text: "#F0F8FF"

spinner:
  waiting_faces:
    - "(◕‿◕)"
    - "(｡◕‿◕｡)"
  thinking_faces:
    - "(¢‿¢)"
    - "(◕ᴗ◕)"
  thinking_verbs:
    - "thinking"
    - "pondering"

branding:
  agent_name: "My Drewgent"
  welcome: "Welcome to my agent!"
  goodbye: "See you! ✨"
  response_label: " ⚕ MyAgent "
  prompt_symbol: "❯ "

tool_prefix: "┊"
tool_emojis:
  terminal: "⚔"
  web_search: "🔮"
```

Then set `display.skin: mydesign` in `config.yaml` or use `/skin mydesign` in the CLI.

**What you can customize:**

| Element | Key | Example |
|---------|-----|---------|
| Logo ASCII art | `banner_logo` | `"[bold #FF0000] MY LOGO"` |
| Hero art | `banner_hero` | `"[#CD7F32] ═══════"` |
| Banner colors | `colors.*` | `banner_border: "#CD7F32"` |
| Spinner faces | `spinner.waiting_faces` | `["(◕‿◕)"]` |
| Spinner verbs | `spinner.thinking_verbs` | `["forging", "thinking"]` |
| Spinner wings | `spinner.wings` | `[["⟪⚔", "⚔⟫"]]` |
| Agent name | `branding.agent_name` | `"My Drewgent"` |
| Response label | `branding.response_label` | `" ⚕ Drewgent "` |
| Tool emojis | `tool_emojis.*` | `terminal: "⚔"` |

Built-in skins: `default` (gold kawaii), `ares` (crimson war-god), `mono` (grayscale), `slate` (cool blue).

---

## Project Structure

```
drewgent/
├── run_agent.py          # Core agent loop, tool dispatch
├── cli.py                # Interactive TUI (banner, spinner, input)
├── model_tools.py        # Tool registry and dispatch
├── toolsets.py           # Tool groupings
├── drewgent_state.py       # SQLite session store (FTS5 search)
├── agent/                # Agent internals
│   ├── prompt_builder.py     # System prompt assembly
│   ├── brain_signals.py      # Brain signal tracking
│   ├── signal_processor.py   # Workflow state machine
│   ├── auto_learn.py        # Wiki maintenance, gap detection
│   └── display.py           # KawaiiSpinner
├── drewgent_cli/           # CLI commands
│   ├── setup.py             # Interactive setup wizard
│   ├── auth.py              # Provider authentication
│   ├── skin_engine.py       # Skin/theme engine
│   ├── banner.py            # Banner ASCII art
│   └── commands.py          # Slash command registry
├── tools/                # Tool implementations
├── gateway/              # Messaging platform gateway
└── docs/
    └── DREWGENT_ARCHITECTURE.md
```

---

## Development

```bash
# Install
git clone https://github.com/adm-humanerd/drewgent.git
cd drewgent
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[all]"

# Test
pytest tests/ -q

# Run
drewgent
```

---

## Customizing Further

### Adding a new LLM provider to the code

Providers are defined in `drewgent_cli/auth.py` (`PROVIDER_REGISTRY`) and `drewgent_cli/models.py`. To add a new provider:

1. Add a `ProviderConfig` entry in `PROVIDER_REGISTRY`
2. Add model list to `_DEFAULT_PROVIDER_MODELS` in `setup.py`
3. Register any special handling in `models.py` if needed

### Brain governance

Drewgent's behavior is governed by neuron files in `P0-brainstem/brain/`. This is specific to this fork and not part of the upstream Hermes-Agent.

---

## License

MIT — [HUMANERD](https://humanerd.ai)