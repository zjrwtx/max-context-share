r"""Export command: package skills + workspace + config fragment.

Scans all skill source directories, collects workspace files,
extracts a safe config fragment, and writes everything into a
timestamped ``.tar.gz`` bundle.

The archive layout mirrors the TypeScript version exactly::

    <timestamp>-openclaw-context/
    ├── manifest.json
    ├── skills/<source>/<slug>/…
    ├── workspace/<FILE>.md
    └── config-fragment.json   (optional)
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .config_fragment import (
    ConfigFragment,
    extract_config_fragment,
)
from .manifest import (
    SkillEntry,
    create_manifest,
    skill_archive_path,
)
from .paths import (
    WORKSPACE_FILES,
    SkillSource,
    SkillSourceDir,
    resolve_paths,
)

# ── Data classes ─────────────────────────────────────────

@dataclass
class ExportOptions:
    r"""Options controlling what gets exported.

    Attributes:
        output (Optional[str]): Output file path.
        skills (Optional[list[str]]): Specific slugs.
        all_skills (bool): Include all skills.
        sources (Optional[list[SkillSource]]): Filter by
            source type.
        no_workspace (bool): Exclude workspace files.
        no_config_fragment (bool): Exclude config fragment.
        agent_id (Optional[str]): Agent ID (future use).
        dry_run (bool): Preview without creating archive.
        json_output (bool): Output result as JSON.
    """

    output: Optional[str] = None
    skills: Optional[List[str]] = None
    all_skills: bool = False
    sources: Optional[List[SkillSource]] = None
    no_workspace: bool = False
    no_config_fragment: bool = False
    agent_id: Optional[str] = None
    dry_run: bool = False
    json_output: bool = False


@dataclass
class ExportResult:
    r"""Result of an export operation.

    Attributes:
        output_file (str): Path to the created archive.
        skills (list[SkillEntry]): Skills included.
        workspace_files (list[str]): Workspace files.
        has_config_fragment (bool): Config presence flag.
        dry_run (bool): Whether this was a dry run.
    """

    output_file: str = ""
    skills: List[SkillEntry] = field(default_factory=list)
    workspace_files: List[str] = field(
        default_factory=list,
    )
    has_config_fragment: bool = False
    dry_run: bool = False


# ── Public API ───────────────────────────────────────────

def run_export(opts: ExportOptions) -> ExportResult:
    r"""Execute the export operation.

    1. Resolve paths from environment
    2. Scan skill sources (ascending precedence)
    3. Filter by --skills if provided
    4. Collect workspace files
    5. Extract config fragment (safe fields only)
    6. Stage and create .tar.gz (unless --dry-run)

    Args:
        opts: Export configuration options.

    Returns:
        An ``ExportResult`` describing what was exported.

    Raises:
        RuntimeError: If requested skills are not found.
    """
    paths = resolve_paths()

    # ── 1. Collect skills from all sources ───────────
    # Higher-precedence sources override same-slug entries
    slug_map: Dict[str, _SkillRecord] = {}

    for src in paths.skill_sources:
        if opts.sources and src.source not in opts.sources:
            continue
        slugs = _list_skill_slugs(src.dir)
        for slug in slugs:
            slug_map[slug] = _SkillRecord(
                entry=SkillEntry(
                    slug=slug, source=src.source,
                ),
                dir=src.dir,
            )

    # Filter to requested slugs
    if opts.skills:
        unknown = [
            s for s in opts.skills if s not in slug_map
        ]
        if unknown:
            raise RuntimeError(
                f"Unknown skills: {', '.join(unknown)}"
            )
        selected = [slug_map[s] for s in opts.skills]
    else:
        selected = list(slug_map.values())

    # ── 2. Collect workspace files ───────────────────
    ws_files: List[str] = []
    if not opts.no_workspace:
        for fname in WORKSPACE_FILES:
            fpath = paths.workspace_dir / fname
            if fpath.is_file():
                ws_files.append(fname)

    # ── 3. Config fragment ───────────────────────────
    config_frag: Optional[ConfigFragment] = None
    if not opts.no_config_fragment:
        config_frag = extract_config_fragment(
            paths.config_file,
        )

    result = ExportResult(
        skills=[r.entry for r in selected],
        workspace_files=ws_files,
        has_config_fragment=config_frag is not None,
        dry_run=opts.dry_run,
    )

    if opts.dry_run:
        if not opts.json_output:
            _print_dry_run(result, paths.skill_sources)
        return result

    # ── 4. Determine output path ─────────────────────
    ts = (
        datetime.now(timezone.utc)
        .isoformat()
        .replace(":", "-")
        .replace(".", "-")
        .replace("T", "_")[:19]
    )
    default_out = os.path.join(
        os.getcwd(), f"{ts}-openclaw-context.tar.gz",
    )
    output_file = (
        os.path.abspath(opts.output)
        if opts.output
        else default_out
    )
    result.output_file = output_file

    # ── 5. Build tar archive in temp dir ─────────────
    tmp_dir = tempfile.mkdtemp(prefix="max-ctx-export-")
    try:
        root_name = f"{ts}-openclaw-context"
        stage = Path(tmp_dir) / root_name
        stage.mkdir(parents=True)

        # Write manifest.json
        manifest = create_manifest(
            skills=result.skills,
            workspace_files=ws_files,
            has_config_fragment=config_frag is not None,
        )
        manifest_path = stage / "manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(
                by_alias=True, indent=2,
            ),
            encoding="utf-8",
        )

        # Copy skills → skills/<source>/<slug>/
        for rec in selected:
            src_dir = rec.dir / rec.entry.slug
            dst_dir = stage / skill_archive_path(rec.entry)
            _copy_dir(src_dir, dst_dir)

        # Copy workspace files
        if ws_files:
            ws_stage = stage / "workspace"
            ws_stage.mkdir(parents=True, exist_ok=True)
            for fname in ws_files:
                shutil.copy2(
                    paths.workspace_dir / fname,
                    ws_stage / fname,
                )

        # Write config fragment
        if config_frag is not None:
            cf_path = stage / "config-fragment.json"
            cf_path.write_text(
                json.dumps(
                    config_frag.model_dump(
                        exclude_none=True,
                    ),
                    indent=2,
                ),
                encoding="utf-8",
            )

        # Create tar.gz
        with tarfile.open(output_file, "w:gz") as tar:
            tar.add(str(stage), arcname=root_name)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return result


async def async_run_export(
    opts: ExportOptions,
) -> ExportResult:
    r"""Async wrapper for ``run_export``.

    Runs the sync function in a thread pool.

    Args:
        opts: Export configuration options.

    Returns:
        An ``ExportResult``.
    """
    return await asyncio.to_thread(run_export, opts)


# ── Private helpers ──────────────────────────────────────

@dataclass
class _SkillRecord:
    r"""Internal: pairs a SkillEntry with its source dir.

    Attributes:
        entry (SkillEntry): The manifest entry.
        dir (Path): The parent source directory.
    """

    entry: SkillEntry
    dir: Path


def _list_skill_slugs(directory: Path) -> List[str]:
    r"""List subdirectory names in a skill source dir.

    Args:
        directory: Path to scan.

    Returns:
        Sorted list of subdirectory names (slugs).
    """
    try:
        return sorted(
            e.name
            for e in directory.iterdir()
            if e.is_dir()
        )
    except FileNotFoundError:
        return []


def _copy_dir(src: Path, dst: Path) -> None:
    r"""Recursively copy a directory tree.

    Args:
        src: Source directory.
        dst: Destination directory (created if needed).
    """
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            _copy_dir(item, target)
        else:
            shutil.copy2(item, target)


def _print_dry_run(
    result: ExportResult,
    skill_sources: Sequence[SkillSourceDir],
) -> None:
    r"""Print a human-readable dry-run summary.

    Args:
        result: The export result to summarise.
        skill_sources: Available source directories.
    """
    print("[dry-run] Would export:")

    if result.skills:
        # Group by source for readability
        by_source: Dict[str, List[str]] = {}
        for e in result.skills:
            by_source.setdefault(e.source, []).append(
                e.slug,
            )
        print("  Skills:")
        for source, slugs in by_source.items():
            src_def = next(
                (s for s in skill_sources
                 if s.source == source),
                None,
            )
            dir_hint = (
                str(src_def.dir) if src_def else ""
            )
            print(f"    [{source}]  {dir_hint}")
            for slug in slugs:
                print(f"      - {slug}")
    else:
        print("  Skills: (none)")

    if result.workspace_files:
        print("  Workspace files:")
        for f in result.workspace_files:
            print(f"    - {f}")
    else:
        print("  Workspace files: (none)")

    has_cf = "yes" if result.has_config_fragment else "no"
    print(f"  Config fragment: {has_cf}")
