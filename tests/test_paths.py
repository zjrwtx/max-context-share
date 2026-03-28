r"""Tests for max_context_share.paths module.

Covers:
  1. Default paths when no env vars set
  2. OPENCLAW_STATE_DIR override
  3. OPENCLAW_PROFILE changes workspace dir name
  4. Default profile uses "workspace"
  5. WORKSPACE_FILES constant has 8 entries
  6. skill_sources filters to existing dirs only
  7. resolve_bundled_skills_dir with env override
  8. resolve_bundled_skills_dir returns None on miss
  9. SkillSourceDir is frozen dataclass
  10. OpenClawPaths config_file points to openclaw.json
"""

from __future__ import annotations

from pathlib import Path

import pytest

from max_context_share.paths import (
    WORKSPACE_FILES,
    SkillSourceDir,
    resolve_bundled_skills_dir,
    resolve_paths,
)


def test_default_paths(tmp_path: Path):
    """resolve_paths uses ~/.openclaw when no env set."""
    home = tmp_path / "home"
    home.mkdir()
    env = {"HOME": str(home)}
    p = resolve_paths(env)
    assert p.state_dir == home / ".openclaw"
    assert p.workspace_dir == home / ".openclaw" / "workspace"


def test_state_dir_override(tmp_path: Path):
    """OPENCLAW_STATE_DIR overrides default state dir."""
    custom = tmp_path / "custom"
    custom.mkdir()
    env = {
        "HOME": str(tmp_path),
        "OPENCLAW_STATE_DIR": str(custom),
    }
    p = resolve_paths(env)
    assert p.state_dir == custom.resolve()


def test_profile_changes_workspace_dir(tmp_path: Path):
    """OPENCLAW_PROFILE creates workspace-<profile>."""
    env = {
        "HOME": str(tmp_path),
        "OPENCLAW_PROFILE": "prod",
    }
    p = resolve_paths(env)
    assert p.workspace_dir.name == "workspace-prod"


def test_default_profile_uses_workspace(tmp_path: Path):
    """Profile 'default' uses plain 'workspace'."""
    env = {
        "HOME": str(tmp_path),
        "OPENCLAW_PROFILE": "default",
    }
    p = resolve_paths(env)
    assert p.workspace_dir.name == "workspace"


def test_workspace_files_constant():
    """WORKSPACE_FILES has exactly 8 entries."""
    assert len(WORKSPACE_FILES) == 8
    assert "AGENTS.md" in WORKSPACE_FILES
    assert "MEMORY.md" in WORKSPACE_FILES


def test_skill_sources_filters_existing(tmp_path: Path):
    """Only existing directories appear in skill_sources."""
    home = tmp_path / "home"
    state = home / ".openclaw"
    skills_dir = state / "skills"
    skills_dir.mkdir(parents=True)
    env = {"HOME": str(home)}
    p = resolve_paths(env)
    sources = [s.source for s in p.skill_sources]
    assert "managed" in sources
    # personal-agents dir doesn't exist
    assert "personal-agents" not in sources


def test_bundled_env_override(tmp_path: Path):
    """resolve_bundled_skills_dir honours env var."""
    bd = tmp_path / "bundled"
    bd.mkdir()
    env = {"OPENCLAW_BUNDLED_SKILLS_DIR": str(bd)}
    result = resolve_bundled_skills_dir(env)
    assert result == bd


def test_bundled_returns_none_on_miss():
    """resolve_bundled_skills_dir returns None when not found."""
    env = {"OPENCLAW_BUNDLED_SKILLS_DIR": "/no/such/path"}
    result = resolve_bundled_skills_dir(env)
    assert result is None


def test_skill_source_dir_frozen():
    """SkillSourceDir is a frozen dataclass."""
    s = SkillSourceDir(
        source="managed", dir=Path("/tmp/skills"),
    )
    with pytest.raises(AttributeError):
        s.source = "workspace"  # type: ignore[misc]


def test_config_file_path(tmp_path: Path):
    """config_file points to openclaw.json."""
    env = {"HOME": str(tmp_path)}
    p = resolve_paths(env)
    assert p.config_file.name == "openclaw.json"
    assert p.config_file.parent == p.state_dir
