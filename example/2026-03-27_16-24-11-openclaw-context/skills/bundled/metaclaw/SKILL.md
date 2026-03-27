---
name: metaclaw
description: >
  Use this skill whenever the user mentions MetaClaw,
  metaclaw CLI, agent meta-learning, agent evolution,
  agent proxy, skill injection, MadMax scheduler,
  conversation RL training, agent memory, PRM scoring,
  or any MetaClaw operations. Also trigger when users
  ask about setting up an auto-learning agent, continuous
  agent training from conversations, skill evolution from
  failures, long-term agent memory, idle-window training
  scheduling, hot-swapping model weights, or connecting
  personal agents (OpenClaw, CoPaw, IronClaw, PicoClaw,
  ZeroClaw, NanoClaw, NemoClaw, Hermes) to cloud RL.
  Use this skill even if the user just mentions
  "metaclaw" or "agent evolution" — it covers the full
  MetaClaw ecosystem including CLI, proxy server, skill
  manager, memory subsystem, and Tinker RL integration.
---

# MetaClaw Skill

MetaClaw is an agent meta-learning framework that turns
personal agents into continuously learning systems. It
sits as an OpenAI-compatible proxy between agents and
LLMs, injecting skills, maintaining long-term memory,
collecting training data, and fine-tuning weights via
cloud RL (Tinker/MinT/Weaver).

**Source repos:**
- MetaClaw: https://github.com/zjrwtx/max_skills
- Tinker SDK: https://github.com/thinking-machines-lab/tinker
- Cookbook: https://github.com/thinking-machines-lab/tinker-cookbook

**IMPORTANT — Always use the latest version:**
```bash
cd <metaclaw-dir> && git pull && uv pip install -e ".[all]"
```
When you need more detailed information, always check
the latest code from these repos.

---

## Quick Start

### Installation

```bash
# Core only (skills_only mode)
uv pip install -e .

# With RL training (Tinker backend)
uv pip install -e ".[rl]"

# Full stack (RL + skill evolution + scheduler)
uv pip install -e ".[rl,evolve,scheduler]"

# Everything including W&B logging
uv pip install -e ".[all]"
```

### Setup & Launch

```bash
# 1. Interactive setup wizard
metaclaw setup

# 2. Start proxy (auto mode — RL + scheduler)
metaclaw start --mode auto

# 3. Check health
metaclaw status

# 4. Stop
metaclaw stop
```

### Key File Locations

| Path | Purpose |
|------|---------|
| `~/.metaclaw/config.yaml` | Main config |
| `~/.metaclaw/skills/` | Skill definitions |
| `~/.metaclaw/memory/memory.db` | Memory store |
| `~/.metaclaw/metaclaw_{port}.pid` | PID file |

---

## Operating Modes

| Mode | RL | Skills | Scheduler | Use Case |
|------|----|----|-----------|----------|
| `auto` | ✅ | ✅ | ✅ forced | Autonomous agent evolution |
| `skills_only` | ❌ | ✅ | ❌ | Safe experimentation, no Tinker needed |
| `rl` | ✅ | ✅ | ❌ | Manual RL control |

```bash
metaclaw start --mode skills_only  # No Tinker needed
metaclaw start --mode rl           # Manual RL
metaclaw start --mode auto         # Full auto
```

---

## CLI Commands

### Root Commands

```bash
# Interactive setup wizard
metaclaw setup

# Start the proxy + RL service
metaclaw start [--mode auto|skills_only|rl] \
  [--port PORT] [-c CONFIG_PATH]

# Stop the running instance
metaclaw stop [--port PORT] [-c CONFIG_PATH]

# Health check
metaclaw status [--port PORT] [-c CONFIG_PATH]

# View or modify config
metaclaw config show
metaclaw config <KEY> <VALUE>
# Examples:
metaclaw config rl.lora_rank 64
metaclaw config memory.enabled true
metaclaw config skills.top_k 8

# Manually trigger one RL training step
metaclaw train-step [--port PORT] \
  [--timeout SECONDS]
```

### Skills Commands

```bash
# View skill evolution history
metaclaw skills log [--n COUNT]
```

### Scheduler Commands

```bash
# Check scheduler state
metaclaw scheduler status

# Manually open/close training window
metaclaw scheduler open-window
metaclaw scheduler close-window
```

### Memory Commands (Core)

```bash
# Memory status and health
metaclaw memory status
metaclaw memory stats
metaclaw memory health
metaclaw memory diagnose
metaclaw memory dashboard

# Search memories
metaclaw memory search <QUERY> [--scope SCOPE]
metaclaw memory search-advanced --keyword KW \
  [--type TYPE] [--tag TAG] [--min-importance N]
metaclaw memory search-regex <PATTERN>

# Import / Export
metaclaw memory export <FILE.jsonl> [--scope SCOPE]
metaclaw memory import <FILE.jsonl> [--scope SCOPE]
metaclaw memory snapshot <NAME>
metaclaw memory restore <NAME>
metaclaw memory backup <OUTPUT_DIR>

# Maintenance
metaclaw memory gc [--scope SCOPE]
metaclaw memory maintenance
metaclaw memory validate
metaclaw memory cleanup-orphans

# Tagging & Organization
metaclaw memory tag <ID> --add <TAG>
metaclaw memory tag <ID> --remove <TAG>
metaclaw memory find-tag <TAG>
metaclaw memory scopes
```

> The memory subsystem has 140+ commands. For the full
> list, read `references/cli-reference.md`.

---

## Common Workflows

### 1. First-Time Setup (Skills Only)

```bash
# Install without RL dependency
uv pip install -e .

# Run setup wizard — picks agent, LLM, API key
metaclaw setup

# Start in safe mode (no Tinker needed)
metaclaw start --mode skills_only

# Verify it's working
metaclaw status
```

### 2. Enable RL Training with Tinker

```bash
# Install with RL support
uv pip install -e ".[rl]"

# Configure Tinker credentials
metaclaw config rl.enabled true
metaclaw config rl.tinker_api_key "your-tinker-key"
metaclaw config rl.model "moonshotai/Kimi-K2.5"

# Start with auto mode (scheduler + RL)
metaclaw start --mode auto

# Monitor training
metaclaw status
```

### 3. Manual Training Step

```bash
# Trigger one RL step manually
metaclaw train-step --timeout 600

# Check Tinker for the created run
tinker run list
tinker checkpoint list --run-id <RUN_ID>
```

### 4. MetaClaw + Tinker Full Pipeline

```bash
# MetaClaw collects data → trains via Tinker
metaclaw start --mode auto

# Use Tinker CLI to inspect results
tinker run list
tinker run info <RUN_ID>
tinker checkpoint download \
  tinker://<RUN_ID>/weights/<STEP> -o ./models/

# Push best model to HuggingFace
tinker checkpoint push-hf \
  tinker://<RUN_ID>/sampler_weights/<STEP> \
  -r myorg/my-agent --public
```

### 5. Memory Management

```bash
# Check memory health
metaclaw memory health
metaclaw memory stats

# Search for something
metaclaw memory search "user preference for dark mode"

# Export for backup
metaclaw memory export backup.jsonl

# Full maintenance cycle
metaclaw memory maintenance
```

### 6. Skill Evolution Monitoring

```bash
# See recent skill evolution events
metaclaw skills log --n 20

# Browse skill files
ls ~/.metaclaw/skills/

# Check evolution history
cat ~/.metaclaw/skills/evolution_history.jsonl
```

---

## Configuration Reference

### Essential Config Fields

```yaml
# ~/.metaclaw/config.yaml
mode: auto  # auto | skills_only | rl

llm:
  provider: custom       # custom | bedrock
  model_id: "model-name"
  api_base: "https://..."
  api_key: "your-key"

proxy:
  port: 30000
  host: "0.0.0.0"

skills:
  enabled: true
  dir: ~/.metaclaw/skills
  retrieval_mode: hybrid  # template|embedding|hybrid
  top_k: 6
  auto_evolve: true
  evolution_every_n_turns: 10

rl:
  enabled: false
  model: "moonshotai/Kimi-K2.5"
  tinker_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""    # tinker://... path

memory:
  enabled: false
  dir: ~/.metaclaw/memory
  scope: default
  retrieval_mode: hybrid  # keyword|embedding|hybrid
  max_injected_units: 6
  max_injected_tokens: 800
  auto_extract: true

scheduler:
  enabled: false          # auto mode forces true
  idle_threshold_minutes: 30
  sleep_start: "23:00"
  sleep_end: "07:00"
  min_window_minutes: 15
```

> For all 40+ config fields, read
> `references/cli-reference.md`.

---

## Tinker Integration

MetaClaw uses Tinker as its RL training backend:

```
Conversation → Data Collection → GRPO Advantages
  → tinker.Datum → forward_backward → optim_step
  → Hot-swap weights → Updated agent
```

Key integration points:
- `metaclaw/trainer.py` — Calls `tinker.ServiceClient`
- `metaclaw/data_formatter.py` — Converts samples to
  `tinker.Datum` objects
- Supports resume from Tinker checkpoint:
  `rl.resume_from_ckpt: "tinker://run/weights/step"`
- Multi-backend: Tinker, MinT, Weaver (auto-detect)

---

## Supported Agents

| Agent | Auto-Config |
|-------|-------------|
| OpenClaw | ✅ Patches `~/.openclaw/openclaw.json` |
| CoPaw | ✅ |
| IronClaw | ✅ |
| PicoClaw | ✅ |
| ZeroClaw | ✅ |
| NanoClaw | ✅ |
| NemoClaw | ✅ |
| Hermes | ✅ |

---

## Quick Troubleshooting

| Problem | Fix |
|---------|-----|
| Setup fails | Check Python 3.10+; `uv pip install -e ".[all]"` |
| Start hangs | Check port 30000 free: `lsof -i :30000` |
| RL not training | Verify `rl.enabled: true` and `rl.tinker_api_key` set |
| Skills not injecting | Check `skills.enabled: true` and `~/.metaclaw/skills/` has `.md` files |
| Memory empty | Enable `memory.enabled: true`; check `memory.auto_extract: true` |
| Scheduler not triggering | Use `--mode auto` (forces scheduler on) |
| Tinker auth error | Check `rl.tinker_api_key`; also set `TINKER_API_KEY` env var |
| Port conflict | Use `--port 30001` or stop existing: `metaclaw stop` |

> For extended error catalog, read
> `references/troubleshooting.md`.

---

## Detailed References

When the SKILL.md cheat sheet is not enough:

- **`references/cli-reference.md`** — All 150+ commands
  with every flag, memory subsystem deep-dive, admin
  API endpoints, all 40+ config fields
- **`references/architecture.md`** — Data flow diagrams,
  Tinker integration internals, memory subsystem,
  skill evolution pipeline, MadMax scheduler logic,
  multi-agent support
- **`references/troubleshooting.md`** — Extended error
  catalog, network issues, Tinker connectivity,
  memory corruption, scheduler debugging
