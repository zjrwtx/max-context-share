# MetaClaw Troubleshooting Guide

Extended error catalog and common fixes for MetaClaw
CLI, proxy, training, memory, and scheduler.

Source: https://github.com/zjrwtx/max_skills

## Table of Contents

1. [Installation Errors](#installation-errors)
2. [Setup & Config Errors](#setup--config-errors)
3. [Start / Stop Errors](#start--stop-errors)
4. [RL Training Errors](#rl-training-errors)
5. [Skills Errors](#skills-errors)
6. [Memory Errors](#memory-errors)
7. [Scheduler Errors](#scheduler-errors)
8. [Tinker Connectivity](#tinker-connectivity)
9. [Agent Integration](#agent-integration)

---

## Installation Errors

### "No module named 'metaclaw'"

```bash
cd <metaclaw-dir>
uv pip install -e .
```

### Missing optional dependencies

| Feature | Fix |
|---------|-----|
| RL mode | `uv pip install -e ".[rl]"` |
| Skill evolution | `uv pip install -e ".[evolve]"` |
| Scheduler | `uv pip install -e ".[scheduler]"` |
| W&B logging | `uv pip install -e ".[all]"` |

### Python version

Requires Python 3.10+:
```bash
python --version
# If too old:
uv venv .venv --python=3.10
```

---

## Setup & Config Errors

### "Config file not found"

```bash
# Create default config
metaclaw setup
# Or manually:
mkdir -p ~/.metaclaw
touch ~/.metaclaw/config.yaml
```

### "Invalid config value"

```bash
# Check current config
metaclaw config show

# Fix with correct types
metaclaw config rl.lora_rank 32        # int
metaclaw config memory.enabled true    # bool
metaclaw config llm.api_key "sk-..."   # string
```

### "Unknown config key"

Use dot-path notation:
```bash
# Correct
metaclaw config rl.tinker_api_key "key"

# Wrong
metaclaw config tinker_api_key "key"
```

Check valid keys:
```bash
metaclaw config show
```

---

## Start / Stop Errors

### "Address already in use" (port conflict)

```bash
# Check what's using the port
lsof -i :30000

# Kill it or use different port
metaclaw start --port 30001
```

### "PID file exists but process not running"

```bash
# Clean up stale PID
rm ~/.metaclaw/metaclaw_30000.pid
metaclaw start
```

### "Cannot connect" on stop/status

The instance might not be running:
```bash
# Check if process exists
cat ~/.metaclaw/metaclaw_30000.pid
ps aux | grep metaclaw

# If dead, clean PID and restart
rm ~/.metaclaw/metaclaw_30000.pid
metaclaw start
```

### Start hangs (no output)

1. Check LLM credentials: `metaclaw config llm.api_key`
2. Check upstream URL: `metaclaw config llm.api_base`
3. Try `--mode skills_only` to isolate RL issues
4. Check logs in terminal (not daemonized by default)

---

## RL Training Errors

### "RL not enabled"

```bash
metaclaw config rl.enabled true
metaclaw config mode rl   # or auto
```

### "Tinker API key not set"

```bash
metaclaw config rl.tinker_api_key "your-key"
# Also set env var for Tinker CLI:
export TINKER_API_KEY="your-key"
```

### "No samples in batch"

The proxy hasn't collected enough conversations yet.
- Check `rl.batch_size` (default: 4)
- Send more requests through the proxy
- Verify the agent is routed through MetaClaw

### "Training step failed"

1. Check Tinker API key is valid
2. Check model name: `metaclaw config rl.model`
3. Check Tinker service status:
   ```bash
   tinker version
   tinker run list --limit 1
   ```
4. Try manual step with longer timeout:
   ```bash
   metaclaw train-step --timeout 1200
   ```

### "Resume checkpoint not found"

Verify the checkpoint path format:
```bash
# Must be a valid tinker:// path
metaclaw config rl.resume_from_ckpt \
  "tinker://run-abc123/weights/step_0003"

# Verify it exists
tinker checkpoint info \
  tinker://run-abc123/weights/step_0003
```

### "GRPO advantage computation failed"

- PRM scorer may be unavailable
- Check `rl.prm_url` and `rl.prm_api_key`
- If no PRM, rewards default to 0 (no learning)

---

## Skills Errors

### "No skills found"

```bash
# Check skills directory
ls ~/.metaclaw/skills/

# Verify config
metaclaw config skills.dir
metaclaw config skills.enabled
```

### "Skills not being injected"

1. Check `skills.enabled: true`
2. Check `skills.top_k` > 0
3. Verify skill files have correct frontmatter:
   ```markdown
   ---
   name: my-skill
   description: When this skill applies
   ---
   ```
4. Check retrieval mode matches your skill format

### "Skill evolution not working"

1. Check `skills.auto_evolve: true`
2. Check evolver LLM config:
   ```bash
   metaclaw config rl.evolver_api_base
   metaclaw config rl.evolver_model
   metaclaw config rl.evolver_api_key
   ```
3. Need enough failed conversations to trigger
   evolution (`evolution_every_n_turns: 10`)

---

## Memory Errors

### "Memory not enabled"

```bash
metaclaw config memory.enabled true
metaclaw start  # restart required
```

### "Memory database locked"

SQLite lock — only one process can write:
```bash
# Stop MetaClaw first
metaclaw stop

# Then run memory commands
metaclaw memory maintenance

# Restart
metaclaw start
```

### "Embedding model not found"

If using embedding retrieval:
```bash
# Check model path
metaclaw config memory.embedding_model_path

# Default: Qwen/Qwen3-Embedding-0.6B
# Will auto-download on first use
# Or switch to keyword-only:
metaclaw config memory.retrieval_mode keyword
metaclaw config memory.use_embeddings false
```

### "Memory store corrupted"

```bash
# Validate
metaclaw memory validate

# Try repair
metaclaw memory maintenance

# If severe, restore from backup
metaclaw memory restore <SNAPSHOT_NAME>

# Last resort: fresh start
rm ~/.metaclaw/memory/memory.db
metaclaw start
```

### "Out of memory with embeddings"

Embedding models use RAM. Options:
1. Disable: `metaclaw config memory.use_embeddings false`
2. Use smaller model
3. Use `keyword` retrieval mode

---

## Scheduler Errors

### "Scheduler not triggering"

1. Must use `--mode auto` (forces scheduler on)
2. Or explicitly enable:
   ```bash
   metaclaw config scheduler.enabled true
   ```
3. Check window config:
   ```bash
   metaclaw scheduler status
   ```

### "Calendar integration not working"

```bash
# Enable calendar
metaclaw config scheduler.calendar.enabled true

# Set credentials path
metaclaw config scheduler.calendar.credentials_path \
  "/path/to/credentials.json"

# Re-authenticate
# Delete token and restart:
rm ~/.metaclaw/calendar_token.json
metaclaw start
```

### "Training only happens at night"

Adjust idle threshold and sleep window:
```bash
metaclaw config scheduler.idle_threshold_minutes 15
metaclaw config scheduler.sleep_start "22:00"
metaclaw config scheduler.sleep_end "08:00"
```

Or manually trigger:
```bash
metaclaw scheduler open-window
metaclaw train-step
```

---

## Tinker Connectivity

### "Tinker connection refused"

1. Check API key: `echo $TINKER_API_KEY`
2. Check MetaClaw config: `metaclaw config rl.tinker_api_key`
3. Test Tinker directly:
   ```bash
   tinker version
   tinker run list --limit 1
   ```
4. Check network/proxy settings

### "Tinker rate limit"

- Reduce training frequency
- Increase `rl.batch_size` (fewer, larger steps)
- Wait and retry

### "Model not available on Tinker"

Verify model name:
```bash
metaclaw config rl.model
# Should be a valid model ID like:
# moonshotai/Kimi-K2.5
# meta-llama/Llama-3.1-8B
```

---

## Agent Integration

### "Agent not routing through MetaClaw"

1. Verify proxy is running: `metaclaw status`
2. Check agent config points to MetaClaw:
   - API base should be `http://localhost:30000`
   - Or whatever port you configured
3. Re-run setup: `metaclaw setup`
4. Check agent-specific config file:
   ```bash
   # For OpenClaw:
   cat ~/.openclaw/openclaw.json
   # Should show api_base → localhost:30000
   ```

### "Agent gets errors after MetaClaw stops"

Agent is still pointing to MetaClaw proxy. Either:
1. Restart MetaClaw: `metaclaw start`
2. Or restore original agent config (saved during
   setup)

### "WeChat agent issues"

```bash
# Force re-login
metaclaw start --wechat-relogin

# Check WeChat enabled
metaclaw config wechat.enabled
```
