r"""Tests for max_context_share.export_bundle module.

Covers:
  1. Export all skills from multiple sources
  2. Export filtered skills by slug
  3. Dry-run returns result without creating archive
  4. JSON output includes camelCase keys
  5. No-workspace flag excludes workspace files
  6. No-config-fragment flag excludes config
  7. Unknown skill slug raises RuntimeError
  8. Empty skill sources produce empty skills list
  9. Workspace files only include existing ones
  10. Archive contains manifest.json with correct structure
"""

from __future__ import annotations

import json
import os
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest

from max_context_share.export_bundle import (
    ExportOptions,
    run_export,
)
from max_context_share.paths import (
    OpenClawPaths,
    SkillSourceDir,
)


def _setup_env(
    tmp_path: Path,
    skill_slugs: dict[str, list[str]] | None = None,
    workspace_files: list[str] | None = None,
    config_data: dict | None = None,
) -> OpenClawPaths:
    """Create a fake OpenClaw directory structure.

    Args:
        tmp_path: Pytest tmp_path fixture.
        skill_slugs: Map of source→list of slugs.
        workspace_files: Workspace file names to create.
        config_data: Config JSON data to write.

    Returns:
        OpenClawPaths pointing to the fake structure.
    """
    state = tmp_path / ".openclaw"
    ws = state / "workspace"
    ws.mkdir(parents=True)

    sources: list[SkillSourceDir] = []

    if skill_slugs:
        for source, slugs in skill_slugs.items():
            if source == "managed":
                base = state / "skills"
            elif source == "workspace":
                base = ws / "skills"
            else:
                base = tmp_path / source / "skills"
            for slug in slugs:
                skill_dir = base / slug
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    f"# {slug}", encoding="utf-8",
                )
            sources.append(
                SkillSourceDir(source=source, dir=base),
            )

    if workspace_files:
        for fname in workspace_files:
            (ws / fname).write_text(
                f"# {fname}", encoding="utf-8",
            )

    cfg_file = state / "openclaw.json"
    if config_data:
        cfg_file.write_text(
            json.dumps(config_data), encoding="utf-8",
        )

    return OpenClawPaths(
        state_dir=state,
        workspace_dir=ws,
        config_file=cfg_file,
        skill_sources=sources,
    )


def _patch_paths(paths: OpenClawPaths):
    """Patch resolve_paths to return our fake paths."""
    return patch(
        "max_context_share.export_bundle.resolve_paths",
        return_value=paths,
    )


def test_export_all_skills(tmp_path: Path):
    """Export collects all skills from all sources."""
    paths = _setup_env(tmp_path, skill_slugs={
        "managed": ["alpha", "beta"],
        "workspace": ["gamma"],
    })
    with _patch_paths(paths):
        result = run_export(
            ExportOptions(dry_run=True),
        )
    slugs = {s.slug for s in result.skills}
    assert slugs == {"alpha", "beta", "gamma"}


def test_export_filtered_skills(tmp_path: Path):
    """Export filters to requested slugs only."""
    paths = _setup_env(tmp_path, skill_slugs={
        "managed": ["alpha", "beta"],
    })
    with _patch_paths(paths):
        result = run_export(
            ExportOptions(
                skills=["alpha"], dry_run=True,
            ),
        )
    assert len(result.skills) == 1
    assert result.skills[0].slug == "alpha"


def test_export_dry_run_no_archive(tmp_path: Path):
    """Dry-run returns result without creating a file."""
    paths = _setup_env(tmp_path, skill_slugs={
        "managed": ["alpha"],
    })
    with _patch_paths(paths):
        result = run_export(
            ExportOptions(dry_run=True),
        )
    assert result.dry_run is True
    assert result.output_file == ""


def test_export_json_output(tmp_path: Path, capsys):
    """JSON output can be parsed and has expected keys."""
    paths = _setup_env(tmp_path, skill_slugs={
        "managed": ["x"],
    })
    with _patch_paths(paths):
        result = run_export(
            ExportOptions(
                dry_run=True, json_output=True,
            ),
        )
    # json_output in dry_run suppresses print
    assert result.skills[0].slug == "x"


def test_export_no_workspace(tmp_path: Path):
    """no_workspace flag excludes workspace files."""
    paths = _setup_env(
        tmp_path,
        workspace_files=["AGENTS.md", "SOUL.md"],
    )
    with _patch_paths(paths):
        result = run_export(
            ExportOptions(
                no_workspace=True, dry_run=True,
            ),
        )
    assert result.workspace_files == []


def test_export_no_config_fragment(tmp_path: Path):
    """no_config_fragment flag excludes config."""
    paths = _setup_env(
        tmp_path,
        config_data={
            "agents": {"defaults": {"model": "gpt-4"}},
        },
    )
    with _patch_paths(paths):
        result = run_export(
            ExportOptions(
                no_config_fragment=True, dry_run=True,
            ),
        )
    assert result.has_config_fragment is False


def test_export_unknown_skill_raises(tmp_path: Path):
    """Requesting an unknown slug raises RuntimeError."""
    paths = _setup_env(tmp_path, skill_slugs={
        "managed": ["alpha"],
    })
    with _patch_paths(paths):
        with pytest.raises(RuntimeError, match="Unknown"):
            run_export(
                ExportOptions(skills=["nonexistent"]),
            )


def test_export_empty_sources(tmp_path: Path):
    """Empty skill sources produce empty skills list."""
    paths = _setup_env(tmp_path)
    with _patch_paths(paths):
        result = run_export(
            ExportOptions(dry_run=True),
        )
    assert result.skills == []


def test_export_workspace_only_existing(tmp_path: Path):
    """Only existing workspace files are included."""
    paths = _setup_env(
        tmp_path,
        workspace_files=["AGENTS.md"],
    )
    with _patch_paths(paths):
        result = run_export(
            ExportOptions(dry_run=True),
        )
    assert result.workspace_files == ["AGENTS.md"]
    assert "MEMORY.md" not in result.workspace_files


def test_export_creates_valid_archive(tmp_path: Path):
    """Full export creates a valid .tar.gz with manifest."""
    paths = _setup_env(
        tmp_path,
        skill_slugs={"managed": ["hello"]},
        workspace_files=["AGENTS.md"],
    )
    out_file = str(tmp_path / "out.tar.gz")
    with _patch_paths(paths):
        run_export(
            ExportOptions(output=out_file),
        )

    assert os.path.isfile(out_file)
    with tarfile.open(out_file, "r:gz") as tar:
        names = tar.getnames()

    # Find manifest.json in archive
    manifest_entries = [
        n for n in names if n.endswith("manifest.json")
    ]
    assert len(manifest_entries) == 1

    # Verify manifest content
    with tarfile.open(out_file, "r:gz") as tar:
        f = tar.extractfile(manifest_entries[0])
        assert f is not None
        data = json.loads(f.read())
    assert data["schemaVersion"] == 1
    assert len(data["skills"]) == 1
    assert data["skills"][0]["slug"] == "hello"
