---
name: max-context-share
description: >-
  Use this skill when the user asks to "export OpenClaw
  skills", "import OpenClaw context", "share OpenClaw
  config", "create a context bundle", "package skills
  for sharing", "backup OpenClaw workspace", or mentions
  max-ctx, max-context-share, context archive, skill
  bundle, or portable OpenClaw setup. Also use when
  troubleshooting export/import errors, understanding
  bundle format, or managing skill sources.
version: 0.1.0
---

# max-context-share

CLI tool (`max-ctx`) to export and import OpenClaw
skills, workspace context files, and config fragments
as a portable `.tar.gz` bundle.

## Quick Start

```bash
# Install globally
npm install -g max-context-share

# Export everything
max-ctx export

# Import a bundle
max-ctx import ./context-bundle.tar.gz
```

## Core Concepts

### Two Commands

| Command | Purpose |
|---------|---------|
| `max-ctx export` | Package skills + workspace + config into `.tar.gz` |
| `max-ctx import <archive>` | Restore bundle into local OpenClaw |

### Skill Sources (Precedence High to Low)

| Source | Path |
|--------|------|
| `workspace` | `<workspace>/skills/` |
| `project-agents` | `<workspace>/.agents/skills/` |
| `personal-agents` | `~/.agents/skills/` |
| `managed` | `~/.openclaw/skills/` |
| `bundled` | `<openclaw-pkg>/skills/` |

When the same slug exists in multiple sources,
the higher-precedence source wins.

### Security Model

The config fragment **never** exports secrets.
Fields containing `secret`, `token`, `key`,
`password`, `auth`, or `credential` are stripped.

Only safe fields are exported:
- `agents.defaults` (model, thinking preferences)
- `agents.list[].skills` (per-agent skill allowlists)
- `skills.allowBundled` / `skills.limits`

Config fragments are **printed but never written**
during import. Apply settings manually via
`openclaw config set ...`.

## Export Options

```bash
# Export all skills + workspace + config
max-ctx export

# Custom output path
max-ctx export --output /tmp/my-bundle.tar.gz

# Export specific skills only
max-ctx export --skills github,weather,discord

# Exclude workspace or config
max-ctx export --no-workspace
max-ctx export --no-config-fragment

# Preview without creating archive
max-ctx export --dry-run

# JSON output for scripting
max-ctx export --dry-run --json
```

## Import Options

```bash
# Merge (default): skip existing files/skills
max-ctx import ./bundle.tar.gz

# Overwrite existing files/skills
max-ctx import ./bundle.tar.gz --overwrite

# Skip workspace files
max-ctx import ./bundle.tar.gz --no-workspace

# Preview changes
max-ctx import ./bundle.tar.gz --dry-run

# JSON output
max-ctx import ./bundle.tar.gz --json
```

## Merge Strategies

| Mode | Skills | Workspace Files |
|------|--------|-----------------|
| `--merge` (default) | Skip existing slugs | Skip existing files |
| `--overwrite` | Replace existing | Overwrite existing |

## Bundle Structure

```
<timestamp>-openclaw-context/
  manifest.json
  skills/
    bundled/<slug>/SKILL.md
    managed/<slug>/SKILL.md
    personal-agents/<slug>/SKILL.md
    project-agents/<slug>/SKILL.md
    workspace/<slug>/SKILL.md
  workspace/
    AGENTS.md, SOUL.md, TOOLS.md,
    IDENTITY.md, USER.md, HEARTBEAT.md,
    BOOTSTRAP.md, MEMORY.md
  config-fragment.json
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENCLAW_STATE_DIR` | `~/.openclaw/` | State directory |
| `OPENCLAW_PROFILE` | (none) | Workspace profile |
| `OPENCLAW_BUNDLED_SKILLS_DIR` | auto-detected | Bundled skills path |

Profile support: `OPENCLAW_PROFILE=prod` resolves
workspace to `~/.openclaw/workspace-prod/`.

## Development

```bash
npm run build       # Compile TypeScript
npm run typecheck   # Type-check only
npm run dev         # Watch mode
node dist/index.js  # Run from source
```

## Troubleshooting

For detailed CLI reference, bundle format specs,
and common error solutions, see:
- `references/cli-reference.md` — Full command docs
- `references/troubleshooting.md` — Error catalog
