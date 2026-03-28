# max-context-share

CLI tool to export and import OpenClaw skills, workspace context files, and config fragments as a portable `.tar.gz` bundle.

> **Note:** This is the Python rewrite of the original TypeScript version. Bundles are **fully compatible** between both versions.

## Running the CLI

### Option A: via pip / uv (recommended)

```bash
# Install with pip
pip install max-context-share

# Or install with uv
uv pip install max-context-share

# Run
max-ctx export
max-ctx import ./sample-context.tar.gz
```

### Option B: run directly from source

Clone or download this repo, then:

```bash
# 1. Enter the project directory
cd max-context-share

# 2. Create venv and install with uv
uv venv .venv --python=3.10
uv sync

# 3. Run via uv
uv run max-ctx export
uv run max-ctx import ./sample-context.tar.gz

# Or activate the venv and run directly
source .venv/bin/activate
max-ctx export --dry-run
```

---

## Usage

### Export

Package your local OpenClaw skills, workspace files, and config fragment into a shareable archive:

```bash
# Export everything (all skills + workspace files + config)
max-ctx export

# Specify output path
max-ctx export --output /tmp/my-context.tar.gz

# Export specific skills only
max-ctx export --skills github,weather,habit-reminder

# Exclude workspace files or config fragment
max-ctx export --no-workspace
max-ctx export --no-config-fragment

# Preview what would be exported
max-ctx export --dry-run

# JSON output (useful for scripting)
max-ctx export --dry-run --json
```

### Import

Import an archive into your local OpenClaw installation:

```bash
# Import with merge strategy (default: skip existing)
max-ctx import /tmp/my-context.tar.gz

# Overwrite existing skills and workspace files
max-ctx import /tmp/my-context.tar.gz --overwrite

# Import only skills, skip workspace files
max-ctx import /tmp/my-context.tar.gz --no-workspace

# Preview what would be imported
max-ctx import /tmp/my-context.tar.gz --dry-run
```

> **Note:** The config fragment is **never written automatically**. On import, its contents are printed so you can review and apply settings manually via `openclaw config set ...`.

---

## Bundle Format

The generated `.tar.gz` contains:

```
<timestamp>-openclaw-context/
  manifest.json              # Metadata: schema version, skills list, etc.
  skills/
    bundled/                 # Skills shipped with openclaw
      <slug>/
        SKILL.md
        ...
    managed/                 # Installed via `openclaw skills install`
      <slug>/
    personal-agents/         # ~/.agents/skills/
      <slug>/
    project-agents/          # <workspace>/.agents/skills/
      <slug>/
    workspace/               # <workspace>/skills/
      <slug>/
  workspace/
    AGENTS.md
    SOUL.md
    TOOLS.md
    IDENTITY.md
    USER.md
    HEARTBEAT.md
    BOOTSTRAP.md
    MEMORY.md
  config-fragment.json       # Safe config subset (no secrets)
```

### Config Fragment

The config fragment only includes safe, non-secret fields from `openclaw.json`:

- `agents.defaults` — model, thinking preferences
- `agents.list[].skills` — per-agent skill allowlists
- `skills.allowBundled` / `skills.limits`

Credentials, tokens, OAuth settings, gateway config, and any field containing `secret`, `token`, `key`, `password`, `auth`, or `credential` are **never exported**.

---

## Skill Sources

OpenClaw loads skills from multiple locations. `max-ctx export` scans all of them:

| Source | Path | Description |
|--------|------|-------------|
| `bundled` | `<openclaw-pkg>/skills/` | Shipped with openclaw (auto-detected via `which openclaw`) |
| `managed` | `~/.openclaw/skills/` | Installed via `openclaw skills install` |
| `personal-agents` | `~/.agents/skills/` | Personal skills shared across all workspaces |
| `project-agents` | `<workspace>/.agents/skills/` | Project-local skills (can be committed to git) |
| `workspace` | `<workspace>/skills/` | Workspace-local skills |

Precedence on conflict (same slug): `workspace` > `project-agents` > `personal-agents` > `managed` > `bundled`.

---

## Merge Strategies

| Mode | Skills | Workspace files |
|------|--------|-----------------|
| `--merge` (default) | Skip existing slugs, print warning | Skip existing files, print notice |
| `--overwrite` | Replace existing slugs entirely | Overwrite existing files |

---

## Paths

Paths are resolved from environment variables (same conventions as OpenClaw core):

| Path | Default | Override |
|------|---------|---------|
| State directory | `~/.openclaw/` | `OPENCLAW_STATE_DIR` |
| Workspace | `~/.openclaw/workspace/` | `OPENCLAW_PROFILE` |
| Managed skills | `~/.openclaw/skills/` | — |
| Config file | `~/.openclaw/openclaw.json` | — |
| Bundled skills | auto-detected from `openclaw` binary | `OPENCLAW_BUNDLED_SKILLS_DIR` |

Profile support: if `OPENCLAW_PROFILE=prod`, workspace resolves to `~/.openclaw/workspace-prod/`.

---

## Python API (Sync + Async)

You can also use `max-context-share` as a library:

```python
from max_context_share.export_bundle import (
    ExportOptions, run_export, async_run_export,
)
from max_context_share.import_bundle import (
    ImportOptions, run_import, async_run_import,
)

# Sync
result = run_export(ExportOptions(dry_run=True))
print(result.skills)

# Async
import asyncio
result = asyncio.run(
    async_run_export(ExportOptions(dry_run=True))
)
```

---

## Example

An example bundle is included in the `example/` directory:

```bash
# Inspect the example bundle
tar tf example/sample-context.tar.gz

# Do a dry-run import to see what would change
max-ctx import example/sample-context.tar.gz --dry-run
```

---

## Development

```bash
# Setup
uv venv .venv --python=3.10
uv sync

# Lint
uv run ruff check src/ tests/

# Test (60 tests across 6 modules)
uv run pytest -v

# Run from source
uv run max-ctx --help
uv run max-ctx export --dry-run
```

---

## Cross-Compatibility

Bundles created by the Python version are **fully compatible** with the TypeScript version and vice versa:

- `manifest.json` uses identical camelCase keys (`schemaVersion`, `createdAt`, `workspaceFiles`, `hasConfigFragment`)
- Archive directory layout is identical
- Same 8 workspace files, same skill source precedence
- Same config fragment safe-field extraction
