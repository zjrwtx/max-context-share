# MetaClaw Architecture Deep-Dive

Covers data flow, Tinker integration internals, memory
subsystem, skill evolution, MadMax scheduler, and
multi-agent support.

Source: https://github.com/zjrwtx/max_skills

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Data Flow](#data-flow)
3. [Tinker Integration](#tinker-integration)
4. [Skill System](#skill-system)
5. [Memory Subsystem](#memory-subsystem)
6. [MadMax Scheduler](#madmax-scheduler)
7. [Multi-Agent Support](#multi-agent-support)
8. [API Server](#api-server)

---

## System Architecture

```
Personal Agent (OpenClaw, CoPaw, IronClaw, ...)
    ↓ HTTP (OpenAI-compatible)
MetaClaw Proxy (FastAPI, port 30000)
    ├→ Skills Injection (template/embedding/hybrid)
    ├→ Memory Retrieval (keyword/embedding/hybrid)
    ├→ PRM Scoring (async reward evaluation)
    └→ Data Collection (→ ConversationSample)
    ↓ HTTP
Upstream LLM (any OpenAI-compatible API)
    ↓
Training Pipeline (when batch ready)
    ├→ Pause data collection
    ├→ Compute GRPO advantages
    ├→ Convert to tinker.Datum
    ├→ Forward/backward on Tinker
    ├→ Hot-swap weights → new SamplingClient
    ├→ Resume data collection
    └→ Skill evolution (async)
```

### Key Files

| Module | LOC | Role |
|--------|-----|------|
| `api_server.py` | 2,700 | FastAPI proxy |
| `trainer.py` | 1,200 | RL training loop |
| `cli.py` | 5,600 | CLI entry point |
| `skill_manager.py` | 800 | Skill load/retrieve |
| `skill_evolver.py` | 600 | Auto-create skills |
| `data_formatter.py` | 230 | Sample → Datum |
| `launcher.py` | 700 | Service orchestration |
| `config_store.py` | 400 | YAML config |
| `prm_scorer.py` | 300 | Reward scoring |
| `scheduler.py` | 300 | Idle/sleep gating |
| `memory/manager.py` | 5,064 | Memory orchestration |
| `memory/store.py` | 1,798 | SQLite FTS5 backend |

---

## Data Flow

### Conversation → Training

1. **Proxy intercepts** request from personal agent
2. **Inject skills** — match task to relevant skills
3. **Inject memory** — retrieve relevant context
4. **Forward to upstream LLM** — get completion
5. **Collect sample** — store as `ConversationSample`
   with tokens, logprobs, and metadata
6. **PRM scores** — async reward evaluation via judge
7. **Batch ready?** — check if `batch_size` reached

### Training Step

1. **Pause** data collection (avoid stale logprobs)
2. **Compute advantages** — GRPO-style reward centering
3. **Format** — `ConversationSample` → `tinker.Datum`
   via `sample_to_datum()` in `data_formatter.py`
4. **Train** — `forward_backward_async()` on Tinker
5. **Optimize** — `optim_step_async()` with AdamParams
6. **Hot-swap** — get new `SamplingClient` with
   updated weights
7. **Resume** data collection with new model
8. **Evolve skills** — async skill extraction from
   failures (if `auto_evolve` enabled)

### ConversationSample Structure

```python
@dataclass
class ConversationSample:
    tokens: list[int]        # Full token sequence
    logprobs: list[float]    # Per-token logprobs
    advantages: list[float]  # GRPO advantages
    reward: float            # PRM scalar reward
    metadata: dict           # Task, agent, timestamp
```

### Datum Conversion

```python
# data_formatter.py
def sample_to_datum(sample: ConversationSample):
    """Convert MetaClaw sample to Tinker Datum."""
    return tinker.Datum(
        tensor_data=tinker.TensorData(
            tokens=sample.tokens,
            logprobs=sample.logprobs,
            advantages=sample.advantages,
        ),
        metadata=sample.metadata,
    )
```

---

## Tinker Integration

### Connection Setup

```python
# trainer.py
service_client = tinker.ServiceClient(
    api_key=config.rl.tinker_api_key
)

training_client = await \
    service_client.training_client_async(
        model_id=config.rl.model,
        lora_rank=config.rl.lora_rank,
    )
```

### Training Loop

```python
# Single RL step
datums = [sample_to_datum(s) for s in batch]

await training_client.forward_backward_async(datums)
await training_client.optim_step_async(
    tinker.AdamParams(learning_rate=1e-4)
)

# Hot-swap: get new sampling client with updated
# weights
sampling_client = await \
    training_client\
    .save_weights_and_get_sampling_client(...)
```

### Resume from Checkpoint

```yaml
# config.yaml
rl:
  resume_from_ckpt: "tinker://run-abc/weights/step_003"
```

### Multi-Backend Support

MetaClaw supports 3 RL backends (auto-detected):
- **Tinker** — Primary, most feature-complete
- **MinT** — Lightweight alternative
- **Weaver** — Third option

Backend is selected automatically based on available
credentials and configuration.

---

## Skill System

### Skill Format

Skills are `.md` files in `~/.metaclaw/skills/`:

```markdown
---
name: my-skill
description: When to use this skill
---

# Skill Instructions

Step-by-step instructions for the agent...
```

### Retrieval Modes

| Mode | How It Works |
|------|-------------|
| `template` | Keyword matching on description |
| `embedding` | Semantic similarity via embeddings |
| `hybrid` | Both, merged + reranked |

Config:
```yaml
skills:
  retrieval_mode: hybrid
  top_k: 6  # Skills injected per request
```

### Skill Evolution

When `auto_evolve: true`, MetaClaw automatically:
1. Detects conversation failures/poor rewards
2. Extracts patterns from failed conversations
3. Generates new skill `.md` files
4. Logs to `evolution_history.jsonl`

Controlled by:
```yaml
skills:
  auto_evolve: true
  evolution_every_n_turns: 10
```

The evolver uses a separate LLM (configured via
`rl.evolver_*` fields) to analyze failures and
synthesize skill definitions.

---

## Memory Subsystem

### Architecture

```
Memory Manager (orchestration)
    ├→ Memory Store (SQLite FTS5)
    ├→ Embedding Index (optional)
    ├→ Policy Engine (retention, consolidation)
    └→ Telemetry (usage tracking)
```

### Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `episodic` | Events, interactions | "User asked about X" |
| `semantic` | Facts, knowledge | "Prefers dark mode" |
| `preference` | User preferences | "Always use Python 3.10" |
| `procedure` | How-to knowledge | "Deploy via `git push`" |

### Retrieval Modes

| Mode | Method | Speed | Quality |
|------|--------|-------|---------|
| `keyword` | SQLite FTS5 | Fast | Good for exact |
| `embedding` | Vector similarity | Slower | Better semantic |
| `hybrid` | Both + rerank | Moderate | Best overall |

### Auto-Extract & Consolidate

When `auto_extract: true`, MetaClaw automatically
extracts memories from conversations:
- User preferences → `preference` type
- Facts learned → `semantic` type
- Events → `episodic` type

When `auto_consolidate: true`, similar memories are
merged to prevent fragmentation.

### Scopes

Memories are organized by scope (namespace):
- `default` — main scope
- Custom scopes for different contexts/projects

```bash
metaclaw memory scopes
metaclaw memory search "query" --scope work
metaclaw memory share <ID> --to personal
```

---

## MadMax Scheduler

The scheduler gates RL training to non-intrusive
windows so the agent doesn't freeze during active use.

### Window Types

| Window | Detection | Config |
|--------|-----------|--------|
| **Idle** | No requests for N minutes | `idle_threshold_minutes: 30` |
| **Sleep** | Time-of-day range | `sleep_start/end` |
| **Calendar** | Google Calendar "busy" events | `calendar.enabled` |

### Logic

```
Is user idle? (no requests for 30 min)
  → YES → open training window

Is it sleep time? (23:00 - 07:00)
  → YES → open training window

Is user in a meeting? (Google Calendar)
  → YES → open training window (they're busy)

Window must be ≥ min_window_minutes (15 min)
```

### Config

```yaml
scheduler:
  enabled: true  # auto mode forces this
  idle_threshold_minutes: 30
  sleep_start: "23:00"
  sleep_end: "07:00"
  min_window_minutes: 15
  calendar:
    enabled: false
    credentials_path: ""
```

### Manual Override

```bash
metaclaw scheduler open-window   # Force open
metaclaw scheduler close-window  # Force close
metaclaw scheduler status        # Current state
```

---

## Multi-Agent Support

MetaClaw auto-configures itself as a proxy for
8+ agent types:

| Agent | Config File | Patch Method |
|-------|------------|--------------|
| OpenClaw | `~/.openclaw/openclaw.json` | Replace `api_base` |
| CoPaw | Agent-specific config | Auto-patch |
| IronClaw | Agent-specific config | Auto-patch |
| PicoClaw | Agent-specific config | Auto-patch |
| ZeroClaw | Agent-specific config | Auto-patch |
| NanoClaw | Agent-specific config | Auto-patch |
| NemoClaw | Agent-specific config | Auto-patch |
| Hermes | Agent-specific config | Auto-patch |

During `metaclaw setup`, the wizard:
1. Detects installed agents
2. Asks which to configure
3. Patches their config to route through MetaClaw proxy
4. Saves original config for rollback

The proxy is transparent — agents don't know they're
going through MetaClaw. Skills and memory are injected
into the system prompt before forwarding.

---

## API Server

### Endpoints

| Path | Method | Format |
|------|--------|--------|
| `/v1/chat/completions` | POST | OpenAI-compatible |
| `/v1/messages` | POST | Anthropic-compatible |
| `/health` | GET | Health check |
| `/admin/status` | GET | Full status JSON |
| `/admin/train-step` | POST | Trigger training |
| `/admin/config` | GET/POST | Config management |

### Request Flow

1. Agent sends chat completion request
2. MetaClaw extracts task instruction
3. Retrieve top-k skills + relevant memories
4. Inject into system prompt
5. Forward to upstream LLM
6. Stream response back to agent
7. Collect sample for training (async)
8. Score with PRM (async)
