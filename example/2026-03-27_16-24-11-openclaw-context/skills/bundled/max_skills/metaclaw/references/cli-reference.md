# MetaClaw CLI — Full Command Reference

Complete reference for every CLI command, flag, config
field, and admin API endpoint.

Source: https://github.com/zjrwtx/max_skills

## Table of Contents

1. [Global Entry Point](#global-entry-point)
2. [Root Commands](#root-commands)
3. [Skills Subgroup](#skills-subgroup)
4. [Scheduler Subgroup](#scheduler-subgroup)
5. [Memory Subgroup](#memory-subgroup)
6. [Admin API Endpoints](#admin-api-endpoints)
7. [Configuration Fields](#configuration-fields)
8. [File Locations](#file-locations)

---

## Global Entry Point

```bash
metaclaw [COMMAND] [OPTIONS]
```

Entry point defined in `pyproject.toml`:
```toml
[project.scripts]
metaclaw = "metaclaw.cli:metaclaw"
```

---

## Root Commands

### metaclaw setup

Interactive setup wizard. Guides through:
1. Choose agent type (OpenClaw, CoPaw, etc.)
2. Configure LLM provider + API key
3. Set operating mode
4. Enable/disable memory, skills, scheduler

No options — fully interactive.

### metaclaw start

Launch the MetaClaw proxy and services.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--mode` | choice | `auto` | `auto`, `skills_only`, `rl` |
| `--port` | int | 30000 | Proxy listen port |
| `-c, --config` | path | `~/.metaclaw/config.yaml` | Config file |
| `--wechat-relogin` | flag | false | Force WeChat re-login |

```bash
metaclaw start --mode auto --port 30000
metaclaw start --mode skills_only
metaclaw start --mode rl -c ./my-config.yaml
```

### metaclaw stop

Stop the running MetaClaw instance.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | int | 30000 | Port of instance to stop |
| `-c, --config` | path | `~/.metaclaw/config.yaml` | Config file |

### metaclaw status

Health check for running instance.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | int | 30000 | Port to check |
| `-c, --config` | path | `~/.metaclaw/config.yaml` | Config file |

### metaclaw config

View or modify configuration.

| Argument | Required | Description |
|----------|----------|-------------|
| `KEY_OR_ACTION` | yes | `show` or dot-path key |
| `VALUE` | no | New value (omit to read) |

```bash
# Show full config
metaclaw config show

# Read a value
metaclaw config rl.lora_rank

# Set a value
metaclaw config rl.lora_rank 64
metaclaw config memory.enabled true
metaclaw config llm.api_key "sk-..."
```

Dot-path examples:
- `mode` — top-level mode
- `llm.provider` — LLM provider
- `rl.tinker_api_key` — Tinker key
- `memory.scope` — memory scope
- `scheduler.sleep_start` — sleep window start
- `skills.retrieval_mode` — skill retrieval

### metaclaw train-step

Manually trigger one RL training step.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | int | 30000 | Instance port |
| `--timeout` | int | 600 | Timeout in seconds |

```bash
metaclaw train-step --timeout 300
```

---

## Skills Subgroup

### metaclaw skills log

View skill evolution history.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--n` | int | 10 | Number of events |

```bash
metaclaw skills log --n 20
```

History stored in:
`~/.metaclaw/skills/evolution_history.jsonl`

---

## Scheduler Subgroup

### metaclaw scheduler status

Show current scheduler state (idle, sleep, calendar
window detection).

### metaclaw scheduler open-window

Manually open a training window (override scheduler).

### metaclaw scheduler close-window

Manually close the training window.

---

## Memory Subgroup

The memory subsystem has 140+ commands organized into
categories. Here are the most important ones:

### Status & Health

```bash
metaclaw memory status         # Policy + store info
metaclaw memory stats          # Detailed analytics
metaclaw memory health         # Health score (0-100)
metaclaw memory diagnose       # Diagnostics
metaclaw memory dashboard      # Operational dashboard
metaclaw memory summary        # Concise overview
```

### Search & Retrieval

```bash
# Keyword search
metaclaw memory search <QUERY> \
  [--scope SCOPE] [--limit N]

# Advanced multi-filter search
metaclaw memory search-advanced \
  --keyword <KW> \
  [--type TYPE] [--tag TAG] \
  [--min-importance N]

# Regex pattern search
metaclaw memory search-regex <PATTERN>

# Context-highlighted search
metaclaw memory search-context <QUERY>

# Find similar memories
metaclaw memory similar <ID> [--limit N]
```

### CRUD Operations

```bash
# Add a memory
metaclaw memory add <CONTENT> \
  [--type TYPE] [--importance N] \
  [--scope SCOPE] [--tag TAG]

# Get by ID
metaclaw memory get <ID>

# Update
metaclaw memory update <ID> --content <TEXT>
metaclaw memory update <ID> --importance <N>

# Delete
metaclaw memory delete <ID> [--force]

# Batch get
metaclaw memory batch-get <ID1> <ID2> ...
```

### Import / Export

```bash
# JSONL format
metaclaw memory export <FILE.jsonl> [--scope SCOPE]
metaclaw memory import <FILE.jsonl> [--scope SCOPE]

# JSON format
metaclaw memory export-json <FILE.json>
metaclaw memory import-json <FILE.json>

# CSV format
metaclaw memory export-csv <FILE.csv>

# ML training format
metaclaw memory export-training <DIR> \
  [--format jsonl|parquet]

# Snapshot (point-in-time backup)
metaclaw memory snapshot <NAME>
metaclaw memory restore <NAME>

# Full backup
metaclaw memory backup <OUTPUT_DIR>
```

### Maintenance

```bash
# Garbage collect expired memories
metaclaw memory gc [--scope SCOPE]

# Full maintenance cycle (gc + consolidate + validate)
metaclaw memory maintenance

# Validate integrity
metaclaw memory validate

# Remove orphaned records
metaclaw memory cleanup-orphans

# Deduplication
metaclaw memory duplicates [--threshold 0.85]
metaclaw memory dedup-report
```

### Tagging & Organization

```bash
# Tag management
metaclaw memory tag <ID> --add <TAG>
metaclaw memory tag <ID> --remove <TAG>
metaclaw memory find-tag <TAG>
metaclaw memory auto-tags <ID>

# Scope management
metaclaw memory scopes
metaclaw memory share <ID> --to <SCOPE>
metaclaw memory compare-scopes <S1> <S2>
metaclaw memory clone-scope <SRC> <DST>
metaclaw memory migrate-scope <SRC> <DST>
```

### TTL & Expiration

```bash
# Set TTL on a memory
metaclaw memory ttl <ID> --seconds <N>
metaclaw memory ttl <ID> --clear

# Type-level TTL policy
metaclaw memory type-ttl <TYPE> --seconds <N>

# Process expired memories
metaclaw memory expire [--scope SCOPE]

# Forecast expirations
metaclaw memory expiry-forecast [--days 30]
```

### Analysis

```bash
# Comprehensive analytics (JSON)
metaclaw memory analytics

# Freshness scores
metaclaw memory freshness [--scope SCOPE]

# Access frequency (hot/warm/cold)
metaclaw memory access-frequency

# Age distribution
metaclaw memory age-distribution

# Importance histogram
metaclaw memory importance-histogram

# Type balance
metaclaw memory type-balance

# Content density (token accounting)
metaclaw memory content-density
```

### History & Versioning

```bash
# Version chain for a memory
metaclaw memory history <ID>

# Full version tree
metaclaw memory version-tree <ID>

# Lifecycle view
metaclaw memory lifecycle <ID>

# Audit log
metaclaw memory events [--limit N]
```

### Relationships

```bash
# Suggest links between memories
metaclaw memory suggest-links [--limit N]

# Export relationship graph
metaclaw memory link-graph [--format dot|json]

# Graph statistics
metaclaw memory link-stats
```

---

## Admin API Endpoints

When MetaClaw is running, these HTTP endpoints are
available on the proxy port:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | OpenAI-compatible proxy |
| `/v1/messages` | POST | Anthropic-compatible proxy |
| `/health` | GET | Health check |
| `/admin/status` | GET | Full status JSON |
| `/admin/train-step` | POST | Trigger RL step |
| `/admin/config` | GET/POST | View/update config |

---

## Configuration Fields

### Complete Config Structure

```yaml
mode: auto  # auto | skills_only | rl

llm:
  provider: custom        # custom | bedrock
  model_id: ""            # Model identifier
  api_base: ""            # API endpoint URL
  api_key: ""             # API key

proxy:
  port: 30000             # Proxy listen port
  host: "0.0.0.0"         # Bind host

skills:
  enabled: true
  dir: "~/.metaclaw/skills"
  retrieval_mode: hybrid  # template|embedding|hybrid
  top_k: 6               # Skills per request
  task_specific_top_k: 10
  auto_evolve: true       # Auto-create skills
  evolution_every_n_turns: 10

rl:
  enabled: false
  model: ""               # Base model for RL
  tinker_api_key: ""      # Tinker auth
  prm_url: ""             # PRM endpoint
  prm_model: ""           # PRM model name
  prm_api_key: ""         # PRM auth
  lora_rank: 32           # LoRA rank
  batch_size: 4           # Training batch
  resume_from_ckpt: ""    # tinker:// path
  evolver_api_base: ""    # Skill evolver LLM
  evolver_api_key: ""
  evolver_model: ""
  manual_train_trigger: false

memory:
  enabled: false
  dir: "~/.metaclaw/memory"
  scope: default
  retrieval_mode: hybrid  # keyword|embedding|hybrid
  use_embeddings: false
  embedding_model_path: "Qwen/Qwen3-Embedding-0.6B"
  auto_upgrade_enabled: false
  auto_upgrade_interval_seconds: 900
  auto_upgrade_require_review: true
  review_stale_after_hours: 72
  max_injected_units: 6
  max_injected_tokens: 800
  auto_extract: true
  auto_consolidate: true

scheduler:
  enabled: false          # auto mode forces true
  idle_threshold_minutes: 30
  sleep_start: "23:00"
  sleep_end: "07:00"
  min_window_minutes: 15
  calendar:
    enabled: false
    credentials_path: ""
    token_path: "~/.metaclaw/calendar_token.json"

wechat:
  enabled: false
```

---

## File Locations

| Path | Purpose |
|------|---------|
| `~/.metaclaw/config.yaml` | Main configuration |
| `~/.metaclaw/metaclaw_{port}.pid` | Process PID |
| `~/.metaclaw/scheduler_state.json` | Scheduler state |
| `~/.metaclaw/skills/` | Skill .md files |
| `~/.metaclaw/skills/evolution_history.jsonl` | Evolution log |
| `~/.metaclaw/memory/memory.db` | SQLite FTS5 store |
| `~/.metaclaw/memory/policy.json` | Memory policy |
| `~/.metaclaw/memory/telemetry.jsonl` | Telemetry log |
| `~/.metaclaw/calendar_token.json` | Google Calendar |
| `~/.openclaw/openclaw.json` | OpenClaw config |
