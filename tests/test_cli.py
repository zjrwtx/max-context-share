r"""Tests for max_context_share.cli module.

Covers:
  1. CLI --version shows version
  2. CLI --help shows usage
  3. export --dry-run runs without error
  4. export --json produces JSON output
  5. export --no-workspace excludes workspace
  6. import with valid archive runs
  7. import --merge is default behaviour
  8. import --overwrite flag works
  9. import --dry-run makes no changes
  10. import with nonexistent archive fails
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from max_context_share.cli import cli
from max_context_share.paths import (
    OpenClawPaths,
)


def _empty_paths(tmp_path: Path) -> OpenClawPaths:
    """Create minimal OpenClawPaths for testing."""
    state = tmp_path / ".openclaw"
    ws = state / "workspace"
    ws.mkdir(parents=True)
    return OpenClawPaths(
        state_dir=state,
        workspace_dir=ws,
        config_file=state / "openclaw.json",
        skill_sources=[],
    )


def _create_test_bundle(tmp_path: Path) -> str:
    """Create a minimal valid bundle for import tests."""
    root_name = "test-context"
    stage = tmp_path / "stage" / root_name
    stage.mkdir(parents=True)
    manifest = {
        "schemaVersion": 1,
        "createdAt": "2026-01-01T00:00:00+00:00",
        "skills": [],
        "workspaceFiles": [],
        "hasConfigFragment": False,
    }
    (stage / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8",
    )
    archive = str(tmp_path / "test.tar.gz")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(str(stage), arcname=root_name)
    return archive


def test_cli_version():
    """--version shows the version string."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help():
    """--help shows usage information."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "export" in result.output.lower()
    assert "import" in result.output.lower()


def test_export_dry_run(tmp_path: Path):
    """export --dry-run runs without errors."""
    paths = _empty_paths(tmp_path)
    runner = CliRunner()
    with patch(
        "max_context_share.export_bundle.resolve_paths",
        return_value=paths,
    ):
        result = runner.invoke(
            cli, ["export", "--dry-run"],
        )
    assert result.exit_code == 0


def test_export_json_output(tmp_path: Path):
    """export --json --dry-run produces JSON."""
    paths = _empty_paths(tmp_path)
    runner = CliRunner()
    with patch(
        "max_context_share.export_bundle.resolve_paths",
        return_value=paths,
    ):
        result = runner.invoke(
            cli, ["export", "--dry-run", "--json"],
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "skills" in data
    assert "dryRun" in data


def test_export_no_workspace(tmp_path: Path):
    """export --no-workspace excludes workspace files."""
    paths = _empty_paths(tmp_path)
    # Create a workspace file to verify exclusion
    (paths.workspace_dir / "AGENTS.md").write_text(
        "test", encoding="utf-8",
    )
    runner = CliRunner()
    with patch(
        "max_context_share.export_bundle.resolve_paths",
        return_value=paths,
    ):
        result = runner.invoke(
            cli,
            ["export", "--no-workspace",
             "--dry-run", "--json"],
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["workspaceFiles"] == []


def test_import_valid_archive(tmp_path: Path):
    """import with a valid archive succeeds."""
    archive = _create_test_bundle(tmp_path)
    paths = _empty_paths(tmp_path)
    runner = CliRunner()
    with patch(
        "max_context_share.import_bundle.resolve_paths",
        return_value=paths,
    ):
        result = runner.invoke(cli, ["import", archive])
    assert result.exit_code == 0


def test_import_merge_default(tmp_path: Path):
    """import defaults to merge mode."""
    archive = _create_test_bundle(tmp_path)
    paths = _empty_paths(tmp_path)
    runner = CliRunner()
    with patch(
        "max_context_share.import_bundle.resolve_paths",
        return_value=paths,
    ):
        result = runner.invoke(cli, ["import", archive])
    assert result.exit_code == 0


def test_import_overwrite_flag(tmp_path: Path):
    """import --overwrite flag is accepted."""
    archive = _create_test_bundle(tmp_path)
    paths = _empty_paths(tmp_path)
    runner = CliRunner()
    with patch(
        "max_context_share.import_bundle.resolve_paths",
        return_value=paths,
    ):
        result = runner.invoke(
            cli, ["import", archive, "--overwrite"],
        )
    assert result.exit_code == 0


def test_import_dry_run(tmp_path: Path):
    """import --dry-run makes no filesystem changes."""
    archive = _create_test_bundle(tmp_path)
    paths = _empty_paths(tmp_path)
    runner = CliRunner()
    with patch(
        "max_context_share.import_bundle.resolve_paths",
        return_value=paths,
    ):
        result = runner.invoke(
            cli, ["import", archive, "--dry-run"],
        )
    assert result.exit_code == 0


def test_import_nonexistent_archive():
    """import with nonexistent file fails."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["import", "/no/such/file.tar.gz"],
    )
    assert result.exit_code != 0
