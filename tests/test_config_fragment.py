r"""Tests for max_context_share.config_fragment module.

Covers:
  1. Extract agents.defaults (model, thinkingDefault)
  2. Extract agents.list[].skills
  3. Extract skills.allowBundled
  4. Extract skills.limits
  5. Returns None when file is missing
  6. Raises RuntimeError on invalid JSON
  7. Strips unknown/secret fields from defaults
  8. Handles empty config (returns None)
  9. Handles agents without defaults
  10. Async wrapper works correctly
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from max_context_share.config_fragment import (
    async_extract_config_fragment,
    extract_config_fragment,
)


def _write_json(path: Path, data: dict) -> Path:
    """Helper to write a JSON file."""
    path.write_text(
        json.dumps(data), encoding="utf-8",
    )
    return path


def test_extract_agent_defaults(tmp_path: Path):
    """Extracts model and thinkingDefault from defaults."""
    cfg = tmp_path / "openclaw.json"
    _write_json(cfg, {
        "agents": {
            "defaults": {
                "model": "gpt-4",
                "thinkingDefault": "enabled",
                "secretKey": "SHOULD_NOT_APPEAR",
            },
        },
    })
    frag = extract_config_fragment(cfg)
    assert frag is not None
    assert frag.agents is not None
    defaults = frag.agents["defaults"]
    assert defaults["model"] == "gpt-4"
    assert defaults["thinkingDefault"] == "enabled"
    assert "secretKey" not in defaults


def test_extract_agent_skills_list(tmp_path: Path):
    """Extracts agents.list[].skills."""
    cfg = tmp_path / "openclaw.json"
    _write_json(cfg, {
        "agents": {
            "list": [
                {
                    "id": "agent-1",
                    "skills": ["github", "slack"],
                    "credentials": "SHOULD_NOT_APPEAR",
                },
            ],
        },
    })
    frag = extract_config_fragment(cfg)
    assert frag is not None
    assert frag.agents is not None
    agents_list = frag.agents["list"]
    assert len(agents_list) == 1
    assert agents_list[0]["id"] == "agent-1"
    assert agents_list[0]["skills"] == ["github", "slack"]
    assert "credentials" not in agents_list[0]


def test_extract_skills_allow_bundled(tmp_path: Path):
    """Extracts skills.allowBundled."""
    cfg = tmp_path / "openclaw.json"
    _write_json(cfg, {
        "skills": {"allowBundled": True},
    })
    frag = extract_config_fragment(cfg)
    assert frag is not None
    assert frag.skills is not None
    assert frag.skills["allowBundled"] is True


def test_extract_skills_limits(tmp_path: Path):
    """Extracts skills.limits fields."""
    cfg = tmp_path / "openclaw.json"
    _write_json(cfg, {
        "skills": {
            "limits": {
                "maxSkillsInPrompt": 10,
                "maxSkillFileBytes": 50000,
            },
        },
    })
    frag = extract_config_fragment(cfg)
    assert frag is not None
    limits = frag.skills["limits"]
    assert limits["maxSkillsInPrompt"] == 10
    assert limits["maxSkillFileBytes"] == 50000


def test_returns_none_missing_file(tmp_path: Path):
    """Returns None when config file doesn't exist."""
    cfg = tmp_path / "nonexistent.json"
    assert extract_config_fragment(cfg) is None


def test_raises_on_invalid_json(tmp_path: Path):
    """Raises RuntimeError on invalid JSON content."""
    cfg = tmp_path / "bad.json"
    cfg.write_text("{invalid", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Invalid JSON"):
        extract_config_fragment(cfg)


def test_strips_secret_fields(tmp_path: Path):
    """Only whitelisted fields appear in output."""
    cfg = tmp_path / "openclaw.json"
    _write_json(cfg, {
        "agents": {
            "defaults": {
                "model": "gpt-4",
                "apiKey": "sk-secret",
                "oauth": {"token": "xyz"},
            },
        },
        "credentials": {"key": "value"},
        "env": {"SECRET": "hidden"},
    })
    frag = extract_config_fragment(cfg)
    assert frag is not None
    defaults = frag.agents["defaults"]
    assert "apiKey" not in defaults
    assert "oauth" not in defaults
    # Top-level secrets not in fragment
    assert frag.skills is None


def test_empty_config_returns_none(tmp_path: Path):
    """Returns None when config has no safe content."""
    cfg = tmp_path / "openclaw.json"
    _write_json(cfg, {})
    assert extract_config_fragment(cfg) is None


def test_agents_without_defaults(tmp_path: Path):
    """Handles agents section with no defaults key."""
    cfg = tmp_path / "openclaw.json"
    _write_json(cfg, {
        "agents": {
            "list": [
                {"id": "a1", "skills": ["github"]},
            ],
        },
    })
    frag = extract_config_fragment(cfg)
    assert frag is not None
    assert "defaults" not in frag.agents
    assert frag.agents["list"][0]["id"] == "a1"


def test_async_wrapper(tmp_path: Path):
    """async_extract_config_fragment returns same result."""
    cfg = tmp_path / "openclaw.json"
    _write_json(cfg, {
        "agents": {"defaults": {"model": "gpt-4"}},
    })
    sync_result = extract_config_fragment(cfg)
    async_result = asyncio.run(
        async_extract_config_fragment(cfg),
    )
    assert sync_result is not None
    assert async_result is not None
    assert (
        sync_result.agents["defaults"]
        == async_result.agents["defaults"]
    )
