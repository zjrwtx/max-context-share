r"""Tests for max_context_share.manifest module.

Covers:
  1. create_manifest produces correct fields
  2. parse_manifest validates valid data
  3. parse_manifest rejects invalid schema version
  4. parse_manifest rejects missing required fields
  5. Manifest serialises with camelCase aliases
  6. skill_archive_path produces correct paths
  7. SkillEntry accepts all source types
  8. SkillEntry rejects invalid source
  9. Manifest round-trips through JSON
  10. create_manifest sets createdAt as ISO datetime
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from max_context_share.manifest import (
    SkillEntry,
    create_manifest,
    parse_manifest,
    skill_archive_path,
)


def test_create_manifest_fields():
    """create_manifest sets all fields correctly."""
    skills = [SkillEntry(slug="foo", source="managed")]
    m = create_manifest(
        skills=skills,
        workspace_files=["AGENTS.md"],
        has_config_fragment=True,
    )
    assert m.schema_version == 1
    assert m.skills == skills
    assert m.workspace_files == ["AGENTS.md"]
    assert m.has_config_fragment is True


def test_parse_manifest_valid():
    """parse_manifest accepts a valid camelCase dict."""
    raw = {
        "schemaVersion": 1,
        "createdAt": "2026-01-01T00:00:00+00:00",
        "skills": [
            {"slug": "bar", "source": "workspace"},
        ],
        "workspaceFiles": ["SOUL.md"],
        "hasConfigFragment": False,
    }
    m = parse_manifest(raw)
    assert m.schema_version == 1
    assert len(m.skills) == 1
    assert m.skills[0].slug == "bar"


def test_parse_manifest_invalid_schema_version():
    """parse_manifest rejects schema version != 1."""
    raw = {
        "schemaVersion": 2,
        "createdAt": "2026-01-01T00:00:00+00:00",
        "skills": [],
        "workspaceFiles": [],
        "hasConfigFragment": False,
    }
    with pytest.raises(ValidationError):
        parse_manifest(raw)


def test_parse_manifest_missing_fields():
    """parse_manifest rejects missing required fields."""
    with pytest.raises((ValidationError, KeyError)):
        parse_manifest({"schemaVersion": 1})


def test_manifest_camel_case_serialisation():
    """Manifest serialises with camelCase aliases."""
    m = create_manifest(
        skills=[], workspace_files=[], has_config_fragment=False,
    )
    data = json.loads(m.model_dump_json(by_alias=True))
    assert "schemaVersion" in data
    assert "createdAt" in data
    assert "workspaceFiles" in data
    assert "hasConfigFragment" in data
    # Ensure snake_case keys are NOT present
    assert "schema_version" not in data
    assert "created_at" not in data


def test_skill_archive_path_format():
    """skill_archive_path returns skills/<source>/<slug>."""
    entry = SkillEntry(slug="github", source="bundled")
    assert skill_archive_path(entry) == (
        "skills/bundled/github"
    )


def test_skill_entry_all_sources():
    """SkillEntry accepts every valid source type."""
    sources = [
        "bundled", "managed", "personal-agents",
        "project-agents", "workspace",
    ]
    for src in sources:
        e = SkillEntry(slug="test", source=src)
        assert e.source == src


def test_skill_entry_invalid_source():
    """SkillEntry rejects an invalid source string."""
    with pytest.raises(ValidationError):
        SkillEntry(slug="test", source="invalid")


def test_manifest_json_roundtrip():
    """Manifest survives a JSON round-trip."""
    m = create_manifest(
        skills=[
            SkillEntry(slug="a", source="managed"),
        ],
        workspace_files=["TOOLS.md"],
        has_config_fragment=True,
    )
    json_str = m.model_dump_json(by_alias=True)
    loaded = json.loads(json_str)
    m2 = parse_manifest(loaded)
    assert m2.skills[0].slug == "a"
    assert m2.workspace_files == ["TOOLS.md"]
    assert m2.has_config_fragment is True


def test_create_manifest_created_at_is_iso():
    """create_manifest sets createdAt as ISO datetime."""
    m = create_manifest(
        skills=[], workspace_files=[],
        has_config_fragment=False,
    )
    # Should contain 'T' as ISO separator
    assert "T" in m.created_at
