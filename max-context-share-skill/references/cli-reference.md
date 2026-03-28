# max-ctx CLI Reference

Complete reference for all `max-ctx` commands,
options, and flags.

## Global Options

```
max-ctx --version    Show version number
max-ctx --help       Show help for any command
```

## export

Package local OpenClaw skills, workspace files,
and config fragment into a shareable `.tar.gz`.

### Synopsis

```
max-ctx export [options]
```

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `-o, --output <file>` | string | `<timestamp>-openclaw-context.tar.gz` | Output file path |
| `--skills <slugs>` | string | all | Comma-separated skill slugs to include |
| `--all-skills` | boolean | true | Include all managed skills |
| `--no-workspace` | boolean | false | Exclude workspace files |
| `--no-config-fragment` | boolean | false | Exclude config fragment |
| `--agent <id>` | string | — | Agent ID (future use) |
| `--dry-run` | boolean | false | Preview without creating archive |
| `--json` | boolean | false | Output result as JSON |

### Examples

```bash
# Export everything with defaults
max-ctx export

# Export to specific path
max-ctx export -o /tmp/team-context.tar.gz

# Export only 3 skills
max-ctx export --skills github,discord,notion

# Skills only, no workspace or config
max-ctx export --no-workspace --no-config-fragment

# Preview in JSON format
max-ctx export --dry-run --json
```

### Output (non-JSON)

```
✓ Exported to: 20260328-openclaw-context.tar.gz
  Skills: 12
  Workspace files: 8
  Config fragment: yes
```

### Output (JSON)

```json
{
  "outputFile": "20260328-openclaw-context.tar.gz",
  "skills": [
    { "slug": "github", "source": "managed" },
    { "slug": "discord", "source": "workspace" }
  ],
  "workspaceFiles": [
    "AGENTS.md", "SOUL.md", "TOOLS.md"
  ],
  "hasConfigFragment": true
}
```

---

## import

Import skills, workspace files, and config hints
from a `.tar.gz` bundle.

### Synopsis

```
max-ctx import <archive> [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<archive>` | Yes | Path to `.tar.gz` bundle |

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--merge` | boolean | true | Skip existing files/skills |
| `--overwrite` | boolean | false | Replace existing files/skills |
| `--no-skills` | boolean | false | Skip importing skills |
| `--no-workspace` | boolean | false | Skip workspace files |
| `--no-config-fragment` | boolean | false | Skip config fragment hint |
| `--agent <id>` | string | — | Agent ID (future use) |
| `--dry-run` | boolean | false | Preview without changes |
| `--json` | boolean | false | Output as JSON |

### Examples

```bash
# Import with merge (skip existing)
max-ctx import ./team-context.tar.gz

# Overwrite everything
max-ctx import ./team-context.tar.gz --overwrite

# Import skills only
max-ctx import ./bundle.tar.gz --no-workspace

# Preview changes
max-ctx import ./bundle.tar.gz --dry-run --json
```

---

## Skill Source Resolution

Export scans all sources in this order
(highest precedence last):

1. `bundled` — `<openclaw-pkg>/skills/`
   Auto-detected via `which openclaw` or
   `npm root -g`.
2. `managed` — `~/.openclaw/skills/`
3. `personal-agents` — `~/.agents/skills/`
4. `project-agents` — `<workspace>/.agents/skills/`
5. `workspace` — `<workspace>/skills/`

When the same slug appears in multiple sources,
the higher-precedence source wins and only that
version is exported.

Import restores each skill to its original source
directory. If the source directory does not exist,
the skill is skipped with a warning.

---

## Bundle Manifest Schema

```json
{
  "schemaVersion": 1,
  "createdAt": "2026-03-28T00:00:00.000000+00:00",
  "skills": [
    {
      "slug": "github",
      "source": "managed"
    }
  ],
  "workspaceFiles": [
    "AGENTS.md",
    "SOUL.md"
  ],
  "hasConfigFragment": true
}
```

Validated at runtime using Pydantic v2 models.

---

## Config Fragment Fields

Only these safe fields are included:

```json
{
  "agents": {
    "defaults": {
      "model": "claude-sonnet-4-20250514",
      "thinkingDefault": "enabled"
    },
    "list": [
      {
        "id": "default",
        "skills": ["github", "discord"]
      }
    ]
  },
  "skills": {
    "allowBundled": true,
    "limits": {}
  }
}
```

**Never exported:**
- Credentials, tokens, OAuth settings
- Gateway configuration
- Any key matching: `secret`, `token`, `key`,
  `password`, `auth`, `credential`
