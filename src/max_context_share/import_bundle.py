r"""Import command: unpack a .tar.gz context bundle.

Extracts skills and workspace files from a bundle into the
local OpenClaw installation.  The config fragment is **never**
written automatically — it is displayed as a hint for the
user to apply manually.

Merge strategies:
  - ``merge`` (default): skip files/skills that already exist
  - ``overwrite``: replace existing files/skills
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional

from .config_fragment import ConfigFragment
from .manifest import (
    Manifest,
    SkillEntry,
    parse_manifest,
    skill_archive_path,
)
from .paths import resolve_paths

MergeMode = Literal["merge", "overwrite"]


# ── Data classes ─────────────────────────────────────────

@dataclass
class ImportOptions:
    r"""Options controlling import behaviour.

    Attributes:
        merge_mode (MergeMode): ``"merge"`` skips existing,
            ``"overwrite"`` replaces.
        no_skills (bool): Skip importing skills.
        no_workspace (bool): Skip importing workspace files.
        no_config_fragment (bool): Skip config hint.
        agent_id (Optional[str]): Agent ID (future use).
        dry_run (bool): Preview without making changes.
        json_output (bool): Output result as JSON.
    """

    merge_mode: MergeMode = "merge"
    no_skills: bool = False
    no_workspace: bool = False
    no_config_fragment: bool = False
    agent_id: Optional[str] = None
    dry_run: bool = False
    json_output: bool = False


@dataclass
class ImportResult:
    r"""Result of an import operation.

    Attributes:
        manifest (Optional[Manifest]): Parsed manifest.
        skills_imported (list[SkillEntry]): Imported skills.
        skills_skipped (list[SkillEntry]): Skipped skills.
        workspace_files_imported (list[str]): Imported files.
        workspace_files_skipped (list[str]): Skipped files.
        config_fragment_hint (Optional[ConfigFragment]):
            Config data for manual review.
        dry_run (bool): Whether this was a dry run.
    """

    manifest: Optional[Manifest] = None
    skills_imported: List[SkillEntry] = field(
        default_factory=list,
    )
    skills_skipped: List[SkillEntry] = field(
        default_factory=list,
    )
    workspace_files_imported: List[str] = field(
        default_factory=list,
    )
    workspace_files_skipped: List[str] = field(
        default_factory=list,
    )
    config_fragment_hint: Optional[ConfigFragment] = None
    dry_run: bool = False


# ── Public API ───────────────────────────────────────────

def run_import(
    archive_path: str,
    opts: Optional[ImportOptions] = None,
) -> ImportResult:
    r"""Execute the import operation.

    1. Extract archive to temp dir
    2. Find root dir inside archive
    3. Parse + validate manifest
    4. Read config fragment (display only)
    5. Import skills (merge or overwrite)
    6. Import workspace files (merge or overwrite)
    7. Print summary

    Args:
        archive_path: Path to the ``.tar.gz`` bundle.
        opts: Import options. Uses defaults if *None*.

    Returns:
        An ``ImportResult`` describing what was imported.

    Raises:
        RuntimeError: If the archive is invalid or empty.
    """
    if opts is None:
        opts = ImportOptions()

    merge_mode = opts.merge_mode
    paths = resolve_paths()

    # ── 1. Extract archive ───────────────────────────
    tmp_dir = tempfile.mkdtemp(prefix="max-ctx-import-")
    try:
        resolved = os.path.abspath(archive_path)
        with tarfile.open(resolved, "r:gz") as tar:
            tar.extractall(
                path=tmp_dir, filter="data",
            )

        # Find root directory inside the archive
        entries = [
            e for e in Path(tmp_dir).iterdir()
            if e.is_dir()
        ]
        if not entries:
            raise RuntimeError(
                "Archive appears empty or has an "
                "unexpected structure."
            )
        extracted_root = entries[0]

        # ── 2. Read manifest ─────────────────────────
        manifest_path = extracted_root / "manifest.json"
        raw = json.loads(
            manifest_path.read_text(encoding="utf-8"),
        )
        manifest = parse_manifest(raw)

        # ── 3. Read config fragment (display only) ───
        cf_hint: Optional[ConfigFragment] = None
        if (
            not opts.no_config_fragment
            and manifest.has_config_fragment
        ):
            cf_path = (
                extracted_root / "config-fragment.json"
            )
            try:
                cf_data = json.loads(
                    cf_path.read_text(encoding="utf-8"),
                )
                cf_hint = ConfigFragment(**cf_data)
            except Exception:
                pass

        # ── 4. Import skills ─────────────────────────
        skills_imported: List[SkillEntry] = []
        skills_skipped: List[SkillEntry] = []

        if not opts.no_skills and manifest.skills:
            source_to_dir = {
                s.source: s.dir
                for s in paths.skill_sources
            }

            for skill_entry in manifest.skills:
                dst_root = source_to_dir.get(
                    skill_entry.source,
                )
                if dst_root is None:
                    print(
                        f'[warn] Unknown source '
                        f'"{skill_entry.source}" for '
                        f'skill "{skill_entry.slug}", '
                        f'skipping.'
                    )
                    skills_skipped.append(skill_entry)
                    continue

                src_dir = (
                    extracted_root
                    / skill_archive_path(skill_entry)
                )
                dst_dir = dst_root / skill_entry.slug
                exists = dst_dir.is_dir()

                if exists and merge_mode == "merge":
                    skills_skipped.append(skill_entry)
                    if not opts.dry_run:
                        print(
                            f'[skip] Skill '
                            f'"{skill_entry.slug}" '
                            f'({skill_entry.source}) '
                            f'already exists (use '
                            f'--overwrite to replace).'
                        )
                    continue

                if not opts.dry_run:
                    dst_root.mkdir(
                        parents=True, exist_ok=True,
                    )
                    if exists:
                        shutil.rmtree(dst_dir)
                    _copy_dir(src_dir, dst_dir)

                skills_imported.append(skill_entry)

        # ── 5. Import workspace files ────────────────
        ws_imported: List[str] = []
        ws_skipped: List[str] = []

        if (
            not opts.no_workspace
            and manifest.workspace_files
        ):
            if not opts.dry_run:
                paths.workspace_dir.mkdir(
                    parents=True, exist_ok=True,
                )
            ws_extract = extracted_root / "workspace"

            for fname in manifest.workspace_files:
                src_file = ws_extract / fname
                dst_file = paths.workspace_dir / fname
                exists = dst_file.is_file()

                if exists and merge_mode == "merge":
                    ws_skipped.append(fname)
                    if not opts.dry_run:
                        print(
                            f'[skip] Workspace file '
                            f'"{fname}" already exists '
                            f'(use --overwrite to '
                            f'replace).'
                        )
                    continue

                if not opts.dry_run:
                    shutil.copy2(src_file, dst_file)
                ws_imported.append(fname)

        result = ImportResult(
            manifest=manifest,
            skills_imported=skills_imported,
            skills_skipped=skills_skipped,
            workspace_files_imported=ws_imported,
            workspace_files_skipped=ws_skipped,
            config_fragment_hint=cf_hint,
            dry_run=opts.dry_run,
        )

        if opts.json_output:
            _print_json(result)
        else:
            _print_summary(
                result, str(paths.workspace_dir),
            )

        return result

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def async_run_import(
    archive_path: str,
    opts: Optional[ImportOptions] = None,
) -> ImportResult:
    r"""Async wrapper for ``run_import``.

    Runs the sync function in a thread pool.

    Args:
        archive_path: Path to the ``.tar.gz`` bundle.
        opts: Import options.

    Returns:
        An ``ImportResult``.
    """
    return await asyncio.to_thread(
        run_import, archive_path, opts,
    )


# ── Private helpers ──────────────────────────────────────

def _copy_dir(src: Path, dst: Path) -> None:
    r"""Recursively copy a directory tree.

    Args:
        src: Source directory.
        dst: Destination (created if needed).
    """
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            _copy_dir(item, target)
        else:
            shutil.copy2(item, target)


def _print_json(result: ImportResult) -> None:
    r"""Print import result as JSON to stdout.

    Args:
        result: The import result.
    """
    data = {
        "manifest": (
            result.manifest.model_dump(by_alias=True)
            if result.manifest
            else None
        ),
        "skillsImported": [
            s.model_dump() for s in result.skills_imported
        ],
        "skillsSkipped": [
            s.model_dump() for s in result.skills_skipped
        ],
        "workspaceFilesImported": (
            result.workspace_files_imported
        ),
        "workspaceFilesSkipped": (
            result.workspace_files_skipped
        ),
        "configFragmentHint": (
            result.config_fragment_hint.model_dump(
                exclude_none=True,
            )
            if result.config_fragment_hint
            else None
        ),
        "dryRun": result.dry_run,
    }
    print(json.dumps(data, indent=2))


def _print_summary(
    result: ImportResult, workspace_dir: str,
) -> None:
    r"""Print a human-readable import summary.

    Args:
        result: The import result.
        workspace_dir: Path to workspace directory.
    """
    prefix = "[dry-run] " if result.dry_run else ""

    if result.skills_imported:
        print(f"{prefix}Skills imported:")
        for e in result.skills_imported:
            print(f"  \u2713 {e.slug}  [{e.source}]")

    if result.skills_skipped:
        print(f"{prefix}Skills skipped (already exist):")
        for e in result.skills_skipped:
            print(f"  ~ {e.slug}  [{e.source}]")

    if result.workspace_files_imported:
        print(
            f"{prefix}Workspace files imported to "
            f"{workspace_dir}:"
        )
        for f in result.workspace_files_imported:
            print(f"  \u2713 {f}")

    if result.workspace_files_skipped:
        print(
            f"{prefix}Workspace files skipped "
            f"(already exist):"
        )
        for f in result.workspace_files_skipped:
            print(f"  ~ {f}")

    if result.config_fragment_hint is not None:
        print(
            "\n\u26a0\ufe0f  Config fragment detected "
            "\u2014 NOT written automatically."
        )
        print(
            "   Review the settings below and apply "
            "manually via `openclaw config set ...`:\n"
        )
        print(
            json.dumps(
                result.config_fragment_hint.model_dump(
                    exclude_none=True,
                ),
                indent=2,
            )
        )

    no_content = (
        not result.skills_imported
        and not result.workspace_files_imported
        and result.config_fragment_hint is None
    )
    if no_content:
        print(f"{prefix}Nothing to import.")
