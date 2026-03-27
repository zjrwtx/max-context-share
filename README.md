# max-context-share

CLI tool to export and import OpenClaw skills, workspace context files, and config fragments as a portable `.tar.gz` bundle.

## Running the CLI

There are two ways to use `max-ctx` — pick whichever fits your workflow.

### Option A: via npm (recommended for most users)

```bash
# Run once without installing
npx max-context-share export
npx max-context-share import ./sample-context.tar.gz

# Or install globally for repeated use
npm install -g max-context-share
max-ctx export
max-ctx import ./sample-context.tar.gz
```

### Option B: run directly from source (no npm install needed)

Clone or download this package, then run the built output with Node directly:

```bash
# 1. Enter the package directory
cd packages/max-context-share

# 2. Install dependencies
npm install

# 3. Build TypeScript
npm run build

# 4. Run directly with node
node dist/index.js export
node dist/index.js export --output /tmp/my-context.tar.gz
node dist/index.js import /tmp/my-context.tar.gz --dry-run
```

You can also add a shell alias to make it feel like a real command:

```bash
alias max-ctx="node /path/to/packages/max-context-share/dist/index.js"
max-ctx export --dry-run
```

---

## Usage

### Export

Package your local OpenClaw skills, workspace files, and config fragment into a shareable archive:

```bash
# Export everything (all skills from all sources + workspace files + config fragment)
max-ctx export

# Specify output path
max-ctx export --output /tmp/my-context.tar.gz

# Export specific skills only (searched across all skill sources)
max-ctx export --skills github,weather,habit-reminder

# Exclude workspace files or config fragment
max-ctx export --no-workspace
max-ctx export --no-config-fragment

# Preview what would be exported without creating the archive
max-ctx export --dry-run

# Output result as JSON (useful for scripting)
max-ctx export --dry-run --json
```

### Import

Import an archive into your local OpenClaw installation:

```bash
# Import with merge strategy (default: skip existing files/skills)
max-ctx import /tmp/my-context.tar.gz

# Overwrite existing skills and workspace files
max-ctx import /tmp/my-context.tar.gz --overwrite

# Import only skills, skip workspace files
max-ctx import /tmp/my-context.tar.gz --no-workspace

# Preview what would be imported without making changes
max-ctx import /tmp/my-context.tar.gz --dry-run
```

> **Note:** The config fragment is **never written automatically**. On import, its contents are printed so you can review and apply settings manually via `openclaw config set ...`.

---

## Bundle Format

The generated `.tar.gz` contains:

```
<timestamp>-openclaw-context/
  manifest.json              # Metadata: schema version, skills list, workspace files, etc.
  skills/
    bundled/                 # Skills shipped with openclaw
      <slug>/
        SKILL.md
        ...
    managed/                 # Skills installed via `openclaw skills install`
      <slug>/
        SKILL.md
    personal-agents/         # ~/.agents/skills/
      <slug>/
        SKILL.md
    project-agents/          # <workspace>/.agents/skills/
      <slug>/
        SKILL.md
    workspace/               # <workspace>/skills/
      <slug>/
        SKILL.md
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
# Type-check
npm run typecheck   # or: npx tsc --noEmit

# Build
npm run build

# Run directly from built output
node dist/index.js --help
node dist/index.js export --dry-run
```
