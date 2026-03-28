r"""Tests for max_context_share.import_bundle module.

Covers:
  1. Import skills into matching source directories
  2. Merge mode skips existing skills
  3. Overwrite mode replaces existing skills
  4. Import workspace files
  5. Merge mode skips existing workspace files
  6. Dry-run makes no changes
  7. Invalid archive raises RuntimeError
  8. Config fragment hint is read but not written
  9. no_skills flag skips skill import
  10. no_workspace flag skips workspace import
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest

from max_context_share.import_bundle import (
    ImportOptions,
    run_import,
)
from max_context_share.paths import (
    OpenClawPaths,
    SkillSourceDir,
)


def _create_bundle(
    tmp_path: Path,
    skills: list[dict] | None = None,
    workspace_files: list[str] | None = None,
    config_fragment: dict | None = None,
) -> str:
    """Create a test .tar.gz bundle.

    Args:
        tmp_path: Base directory for staging.
        skills: List of {slug, source} dicts.
        workspace_files: Workspace file names.
        config_fragment: Config fragment data.

    Returns:
        Path to the created .tar.gz file.
    """
    root_name = "test-openclaw-context"
    stage = tmp_path / "stage" / root_name
    stage.mkdir(parents=True)

    skill_entries = skills or []
    ws_files = workspace_files or []
    has_cf = config_fragment is not None

    # manifest
    manifest = {
        "schemaVersion": 1,
        "createdAt": "2026-01-01T00:00:00+00:00",
        "skills": skill_entries,
        "workspaceFiles": ws_files,
        "hasConfigFragment": has_cf,
    }
    (stage / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8",
    )

    # skills
    for s in skill_entries:
        skill_dir = (
            stage / "skills" / s["source"] / s["slug"]
        )
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"# {s['slug']}", encoding="utf-8",
        )

    # workspace
    if ws_files:
        ws_dir = stage / "workspace"
        ws_dir.mkdir(parents=True)
        for fname in ws_files:
            (ws_dir / fname).write_text(
                f"# {fname}", encoding="utf-8",
            )

    # config fragment
    if config_fragment:
        (stage / "config-fragment.json").write_text(
            json.dumps(config_fragment), encoding="utf-8",
        )

    # tar it
    archive = str(tmp_path / "bundle.tar.gz")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(str(stage), arcname=root_name)

    return archive


def _setup_dest(
    tmp_path: Path,
    existing_skills: dict[str, list[str]] | None = None,
    existing_ws: list[str] | None = None,
) -> OpenClawPaths:
    """Create a destination OpenClaw structure.

    Args:
        tmp_path: Base directory.
        existing_skills: Pre-existing skills per source.
        existing_ws: Pre-existing workspace files.

    Returns:
        OpenClawPaths for the destination.
    """
    state = tmp_path / "dest" / ".openclaw"
    ws = state / "workspace"
    ws.mkdir(parents=True)

    sources: list[SkillSourceDir] = []

    if existing_skills:
        for source, slugs in existing_skills.items():
            if source == "managed":
                base = state / "skills"
            elif source == "workspace":
                base = ws / "skills"
            else:
                base = tmp_path / "dest" / source / "skills"
            base.mkdir(parents=True, exist_ok=True)
            for slug in slugs:
                sd = base / slug
                sd.mkdir(parents=True)
                (sd / "SKILL.md").write_text(
                    "existing", encoding="utf-8",
                )
            sources.append(
                SkillSourceDir(source=source, dir=base),
            )
    else:
        # Ensure managed dir exists for imports
        managed = state / "skills"
        managed.mkdir(parents=True, exist_ok=True)
        sources.append(
            SkillSourceDir(source="managed", dir=managed),
        )

    if existing_ws:
        for fname in existing_ws:
            (ws / fname).write_text(
                "existing", encoding="utf-8",
            )

    return OpenClawPaths(
        state_dir=state,
        workspace_dir=ws,
        config_file=state / "openclaw.json",
        skill_sources=sources,
    )


def _patch_paths(paths: OpenClawPaths):
    """Patch resolve_paths in import_bundle."""
    return patch(
        "max_context_share.import_bundle.resolve_paths",
        return_value=paths,
    )


def test_import_skills(tmp_path: Path):
    """Import places skills into matching source dirs."""
    archive = _create_bundle(
        tmp_path,
        skills=[
            {"slug": "alpha", "source": "managed"},
        ],
    )
    dest = _setup_dest(tmp_path)
    with _patch_paths(dest):
        result = run_import(archive, ImportOptions())
    assert len(result.skills_imported) == 1
    assert result.skills_imported[0].slug == "alpha"
    skill_dir = dest.skill_sources[0].dir / "alpha"
    assert skill_dir.is_dir()


def test_merge_skips_existing(tmp_path: Path):
    """Merge mode skips already-existing skills."""
    archive = _create_bundle(
        tmp_path,
        skills=[
            {"slug": "alpha", "source": "managed"},
        ],
    )
    dest = _setup_dest(
        tmp_path,
        existing_skills={"managed": ["alpha"]},
    )
    with _patch_paths(dest):
        result = run_import(
            archive,
            ImportOptions(merge_mode="merge"),
        )
    assert len(result.skills_skipped) == 1
    assert len(result.skills_imported) == 0


def test_overwrite_replaces_existing(tmp_path: Path):
    """Overwrite mode replaces existing skills."""
    archive = _create_bundle(
        tmp_path,
        skills=[
            {"slug": "alpha", "source": "managed"},
        ],
    )
    dest = _setup_dest(
        tmp_path,
        existing_skills={"managed": ["alpha"]},
    )
    with _patch_paths(dest):
        result = run_import(
            archive,
            ImportOptions(merge_mode="overwrite"),
        )
    assert len(result.skills_imported) == 1
    # Verify content was replaced
    skill_md = (
        dest.skill_sources[0].dir / "alpha" / "SKILL.md"
    )
    content = skill_md.read_text(encoding="utf-8")
    assert content == "# alpha"


def test_import_workspace_files(tmp_path: Path):
    """Import copies workspace files."""
    archive = _create_bundle(
        tmp_path,
        workspace_files=["AGENTS.md", "SOUL.md"],
    )
    dest = _setup_dest(tmp_path)
    with _patch_paths(dest):
        result = run_import(archive, ImportOptions())
    assert set(result.workspace_files_imported) == {
        "AGENTS.md", "SOUL.md",
    }
    assert (dest.workspace_dir / "AGENTS.md").is_file()


def test_merge_skips_existing_workspace(tmp_path: Path):
    """Merge mode skips existing workspace files."""
    archive = _create_bundle(
        tmp_path,
        workspace_files=["AGENTS.md"],
    )
    dest = _setup_dest(
        tmp_path, existing_ws=["AGENTS.md"],
    )
    with _patch_paths(dest):
        result = run_import(
            archive,
            ImportOptions(merge_mode="merge"),
        )
    assert result.workspace_files_skipped == ["AGENTS.md"]
    assert result.workspace_files_imported == []


def test_dry_run_no_changes(tmp_path: Path):
    """Dry-run reports but makes no file changes."""
    archive = _create_bundle(
        tmp_path,
        skills=[
            {"slug": "alpha", "source": "managed"},
        ],
        workspace_files=["AGENTS.md"],
    )
    dest = _setup_dest(tmp_path)
    with _patch_paths(dest):
        result = run_import(
            archive, ImportOptions(dry_run=True),
        )
    assert result.dry_run is True
    assert len(result.skills_imported) == 1
    # But no file actually written
    skill_dir = dest.skill_sources[0].dir / "alpha"
    assert not skill_dir.exists()


def test_invalid_archive(tmp_path: Path):
    """Invalid archive file raises an error."""
    bad = tmp_path / "bad.tar.gz"
    bad.write_text("not a tarball", encoding="utf-8")
    dest = _setup_dest(tmp_path)
    with _patch_paths(dest):
        with pytest.raises(Exception):
            run_import(str(bad), ImportOptions())


def test_config_fragment_hint_read(tmp_path: Path):
    """Config fragment is read for display, not written."""
    cf_data = {
        "agents": {"defaults": {"model": "gpt-4"}},
    }
    archive = _create_bundle(
        tmp_path, config_fragment=cf_data,
    )
    dest = _setup_dest(tmp_path)
    with _patch_paths(dest):
        result = run_import(archive, ImportOptions())
    assert result.config_fragment_hint is not None
    assert (
        result.config_fragment_hint.agents["defaults"]
        ["model"] == "gpt-4"
    )
    # Config file should NOT be written
    assert not dest.config_file.exists()


def test_no_skills_flag(tmp_path: Path):
    """no_skills flag skips skill import entirely."""
    archive = _create_bundle(
        tmp_path,
        skills=[
            {"slug": "alpha", "source": "managed"},
        ],
    )
    dest = _setup_dest(tmp_path)
    with _patch_paths(dest):
        result = run_import(
            archive,
            ImportOptions(no_skills=True),
        )
    assert result.skills_imported == []
    assert result.skills_skipped == []


def test_no_workspace_flag(tmp_path: Path):
    """no_workspace flag skips workspace file import."""
    archive = _create_bundle(
        tmp_path,
        workspace_files=["AGENTS.md"],
    )
    dest = _setup_dest(tmp_path)
    with _patch_paths(dest):
        result = run_import(
            archive,
            ImportOptions(no_workspace=True),
        )
    assert result.workspace_files_imported == []
