r"""Click CLI for max-context-share (``max-ctx``).

Provides two subcommands:

- ``max-ctx export`` — package skills + workspace + config
  fragment into a ``.tar.gz`` bundle.
- ``max-ctx import`` — unpack a bundle into the local
  OpenClaw installation.

The entry point is the sync ``cli()`` function; async core
logic is invoked via ``asyncio.run()`` where needed.
"""

from __future__ import annotations

import json
import sys

import click

from .export_bundle import ExportOptions, run_export
from .import_bundle import (
    ImportOptions,
    MergeMode,
    run_import,
)


@click.group()
@click.version_option(version="0.1.0", prog_name="max-ctx")
def cli() -> None:
    r"""Export/import OpenClaw skills and config."""


@cli.command()
@click.option(
    "-o", "--output",
    type=click.Path(),
    default=None,
    help=(
        "Output file path "
        "(default: <timestamp>-openclaw-context.tar.gz)"
    ),
)
@click.option(
    "--skills",
    default=None,
    help="Comma-separated skill slugs to include.",
)
@click.option(
    "--all-skills",
    is_flag=True,
    default=False,
    help="Include all managed skills (default behaviour).",
)
@click.option(
    "--no-workspace",
    is_flag=True,
    default=False,
    help="Exclude workspace files.",
)
@click.option(
    "--no-config-fragment",
    is_flag=True,
    default=False,
    help="Exclude config fragment.",
)
@click.option(
    "--agent",
    default=None,
    help="Agent ID (for future use).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="List what would be exported without creating "
         "the archive.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help="Output result as JSON.",
)
def export(
    output: str | None,
    skills: str | None,
    all_skills: bool,
    no_workspace: bool,
    no_config_fragment: bool,
    agent: str | None,
    dry_run: bool,
    json_output: bool,
) -> None:
    r"""Package skills + workspace + config into a .tar.gz bundle."""
    skills_list = (
        [s.strip() for s in skills.split(",") if s.strip()]
        if skills
        else None
    )

    opts = ExportOptions(
        output=output,
        skills=skills_list,
        all_skills=all_skills,
        no_workspace=no_workspace,
        no_config_fragment=no_config_fragment,
        agent_id=agent,
        dry_run=dry_run,
        json_output=json_output,
    )

    try:
        result = run_export(opts)
        if json_output:
            data = {
                "outputFile": result.output_file,
                "skills": [
                    s.model_dump()
                    for s in result.skills
                ],
                "workspaceFiles": result.workspace_files,
                "hasConfigFragment": (
                    result.has_config_fragment
                ),
                "dryRun": result.dry_run,
            }
            click.echo(json.dumps(data, indent=2))
        elif not dry_run:
            click.echo(
                f"\u2713 Exported to: {result.output_file}"
            )
            click.echo(
                f"  Skills: {len(result.skills)}"
            )
            click.echo(
                f"  Workspace files: "
                f"{len(result.workspace_files)}"
            )
            has = (
                "yes" if result.has_config_fragment
                else "no"
            )
            click.echo(f"  Config fragment: {has}")
    except Exception as exc:
        click.echo(f"Export failed: {exc}", err=True)
        sys.exit(1)


@cli.command(name="import")
@click.argument("archive", type=click.Path(exists=True))
@click.option(
    "--merge",
    "merge_flag",
    is_flag=True,
    default=False,
    help="Skip existing files/skills (default).",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing files/skills.",
)
@click.option(
    "--no-skills",
    is_flag=True,
    default=False,
    help="Skip importing skills.",
)
@click.option(
    "--no-workspace",
    is_flag=True,
    default=False,
    help="Skip importing workspace files.",
)
@click.option(
    "--no-config-fragment",
    is_flag=True,
    default=False,
    help="Skip showing config fragment hint.",
)
@click.option(
    "--agent",
    default=None,
    help="Agent ID (for future use).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be imported without changes.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help="Output result as JSON.",
)
def import_cmd(
    archive: str,
    merge_flag: bool,
    overwrite: bool,
    no_skills: bool,
    no_workspace: bool,
    no_config_fragment: bool,
    agent: str | None,
    dry_run: bool,
    json_output: bool,
) -> None:
    r"""Import skills + workspace files from a .tar.gz bundle."""
    merge_mode: MergeMode = "merge"
    if overwrite:
        merge_mode = "overwrite"

    opts = ImportOptions(
        merge_mode=merge_mode,
        no_skills=no_skills,
        no_workspace=no_workspace,
        no_config_fragment=no_config_fragment,
        agent_id=agent,
        dry_run=dry_run,
        json_output=json_output,
    )

    try:
        run_import(archive, opts)
    except Exception as exc:
        click.echo(f"Import failed: {exc}", err=True)
        sys.exit(1)
