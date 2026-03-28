r"""Manifest schema and helpers for .tar.gz context bundles.

Defines the Pydantic models that represent the manifest.json
file inside each bundle, ensuring bundle-compatibility with
the TypeScript version (camelCase JSON keys).

Attributes:
    MANIFEST_SCHEMA_VERSION (int): Current manifest schema
        version. Fixed at 1.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal

from pydantic import BaseModel, Field

MANIFEST_SCHEMA_VERSION: int = 1

# Allowed skill source types, in precedence order (low→high).
SkillSourceLiteral = Literal[
    "bundled",
    "managed",
    "personal-agents",
    "project-agents",
    "workspace",
]


class SkillEntry(BaseModel):
    r"""A single skill entry inside the manifest.

    Attributes:
        slug (str): The skill identifier / directory name.
        source (SkillSourceLiteral): Which source directory
            the skill originated from.
    """

    slug: str
    source: SkillSourceLiteral


class Manifest(BaseModel):
    r"""Root manifest schema for a context bundle.

    All field aliases use camelCase so the serialised JSON
    matches the TypeScript version exactly.

    Attributes:
        schema_version (int): Must be 1.
        created_at (str): ISO-8601 datetime string.
        skills (List[SkillEntry]): Skills in the bundle.
        workspace_files (List[str]): Workspace file names.
        has_config_fragment (bool): Whether a config
            fragment is included.
    """

    schema_version: Literal[1] = Field(
        default=MANIFEST_SCHEMA_VERSION,
        alias="schemaVersion",
    )
    created_at: str = Field(alias="createdAt")
    skills: List[SkillEntry] = Field(default_factory=list)
    workspace_files: List[str] = Field(
        default_factory=list,
        alias="workspaceFiles",
    )
    has_config_fragment: bool = Field(
        default=False,
        alias="hasConfigFragment",
    )

    model_config = {
        "populate_by_name": True,
    }


def create_manifest(
    skills: List[SkillEntry],
    workspace_files: List[str],
    has_config_fragment: bool,
) -> Manifest:
    r"""Build a new Manifest with the current timestamp.

    Args:
        skills: Skill entries to include.
        workspace_files: Workspace file names to include.
        has_config_fragment: Whether a config-fragment.json
            is present in the bundle.

    Returns:
        A fully populated Manifest instance.
    """
    return Manifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        created_at=datetime.now(timezone.utc).isoformat(),
        skills=skills,
        workspace_files=workspace_files,
        has_config_fragment=has_config_fragment,
    )


def parse_manifest(raw: dict) -> Manifest:
    r"""Parse and validate a raw dict into a Manifest.

    Args:
        raw: Dictionary (typically from JSON) to validate.

    Returns:
        A validated Manifest instance.

    Raises:
        pydantic.ValidationError: If the data does not
            conform to the schema.
    """
    return Manifest.model_validate(raw)


def skill_archive_path(entry: SkillEntry) -> str:
    r"""Compute the archive-internal path for a skill.

    Args:
        entry: The skill entry.

    Returns:
        A string like ``skills/<source>/<slug>``.
    """
    return f"skills/{entry.source}/{entry.slug}"
