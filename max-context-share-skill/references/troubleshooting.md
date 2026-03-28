# Troubleshooting max-context-share

Common errors and solutions when using `max-ctx`.

---

## Export Errors

### "No skills found"

**Cause:** No skill directories detected in any
source location.

**Fix:**
1. Verify OpenClaw is installed:
   `which openclaw`
2. Check managed skills exist:
   `ls ~/.openclaw/skills/`
3. Check workspace skills:
   `ls ./skills/`
4. Set environment variable if needed:
   `export OPENCLAW_STATE_DIR=~/.openclaw`

### "Unknown skills: <slug>"

**Cause:** The `--skills` flag references a slug
that does not exist in any source.

**Fix:**
1. Run `max-ctx export --dry-run` to list all
   available skills.
2. Verify the slug spelling matches the directory
   name exactly.

### "Permission denied" on output file

**Cause:** No write access to the output directory.

**Fix:**
1. Use `--output` to specify a writable path:
   `max-ctx export -o ~/Desktop/bundle.tar.gz`
2. Check directory permissions:
   `ls -la /path/to/output/`

### Bundled skills not detected

**Cause:** `which openclaw` fails or OpenClaw was
installed in a non-standard location.

**Fix:**
1. Set the override env var:
   ```bash
   export OPENCLAW_BUNDLED_SKILLS_DIR=\
     /path/to/openclaw/skills
   ```
2. Or ensure `openclaw` is on your `$PATH`.

---

## Import Errors

### "Archive appears empty"

**Cause:** The file is not a valid `.tar.gz` or
does not contain the expected directory structure.

**Fix:**
1. Verify the file: `tar tf archive.tar.gz`
2. Ensure it was created by `max-ctx export`.
3. Check the file is not corrupted.

### "Manifest validation failed"

**Cause:** The `manifest.json` inside the archive
has an invalid or unsupported schema.

**Fix:**
1. Check `schemaVersion` is `1`.
2. Ensure the bundle was not manually edited.
3. Re-export from the source.

### "Skill already exists: <slug>"

**Cause:** Using default `--merge` strategy and
the skill already exists locally.

**Fix:**
- This is expected behavior. The skill is skipped.
- Use `--overwrite` to replace existing skills:
  `max-ctx import bundle.tar.gz --overwrite`

### "Config fragment not applied"

**Cause:** Config fragments are never auto-written.
This is by design for security.

**Fix:**
1. Review the printed config fragment.
2. Apply settings manually:
   ```bash
   openclaw config set agents.defaults.model \
     claude-sonnet-4-20250514
   ```

---

## Environment Issues

### Wrong workspace directory

**Symptom:** Export/import targets unexpected paths.

**Fix:**
1. Check current profile:
   `echo $OPENCLAW_PROFILE`
2. Check state dir:
   `echo $OPENCLAW_STATE_DIR`
3. Unset if needed:
   `unset OPENCLAW_PROFILE`

### Python version too old

**Symptom:** Import errors or syntax errors.

**Fix:**
Requires Python >= 3.10:
```bash
python3 --version
# If < 3.10, upgrade Python or use uv:
uv venv .venv --python=3.10
```

---

## Development Issues

### Module not found errors

```bash
# Reinstall in development mode
uv sync
# Or force editable install
uv pip install -e . --python .venv/bin/python
```

### Lint errors

```bash
# Auto-fix with ruff
uv run ruff check --fix src/ tests/
```

### Running from source

```bash
# Always sync before running
uv sync
uv run max-ctx export --dry-run
```
