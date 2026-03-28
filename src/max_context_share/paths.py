r"""OpenClaw file-system path resolution.

Resolves all relevant OpenClaw directories without depending
on the openclaw core package.  Reads conventions directly
from the file system (``~/.openclaw/``).

Attributes:
    WORKSPACE_FILES (tuple[str, ...]): The 8 canonical
        workspace context file names.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional

# ── Constants ────────────────────────────────────────────

WORKSPACE_FILES: tuple[str, ...] = (
    "AGENTS.md",
    "SOUL.md",
    "TOOLS.md",
    "IDENTITY.md",
    "USER.md",
    "HEARTBEAT.md",
    "BOOTSTRAP.md",
    "MEMORY.md",
)

# Skill source types in ascending precedence.
SkillSource = Literal[
    "bundled",
    "managed",
    "personal-agents",
    "project-agents",
    "workspace",
]


# ── Data classes ─────────────────────────────────────────

@dataclass(frozen=True)
class SkillSourceDir:
    r"""A pairing of a skill source type with its directory.

    Attributes:
        source (SkillSource): The source category.
        dir (Path): Absolute path to the directory.
    """

    source: SkillSource
    dir: Path


@dataclass(frozen=True)
class OpenClawPaths:
    r"""Resolved OpenClaw paths for the current environment.

    Attributes:
        state_dir (Path): ``~/.openclaw``
            (or ``$OPENCLAW_STATE_DIR``).
        workspace_dir (Path): ``~/.openclaw/workspace``
            (or ``workspace-<profile>``).
        config_file (Path): ``~/.openclaw/openclaw.json``.
        skill_sources (list[SkillSourceDir]): All skill
            source directories in ascending precedence,
            filtered to those that exist on disk.
    """

    state_dir: Path
    workspace_dir: Path
    config_file: Path
    skill_sources: List[SkillSourceDir] = field(
        default_factory=list,
    )


# ── Public API ───────────────────────────────────────────

def resolve_paths(
    env: Optional[dict[str, str]] = None,
) -> OpenClawPaths:
    r"""Resolve all relevant OpenClaw paths from the env.

    Mirrors the logic in the TypeScript ``resolvePaths()``.

    Args:
        env: Environment variable mapping.  Defaults to
            ``os.environ`` when *None*.

    Returns:
        An ``OpenClawPaths`` instance with all directories
        resolved and filtered to those that exist.
    """
    if env is None:
        env = dict(os.environ)

    home = Path(
        env.get("HOME")
        or env.get("USERPROFILE")
        or Path.home().as_posix()
    )

    # $OPENCLAW_STATE_DIR overrides ~/.openclaw
    state_dir_raw = env.get("OPENCLAW_STATE_DIR", "")
    state_dir = (
        Path(state_dir_raw).resolve()
        if state_dir_raw.strip()
        else home / ".openclaw"
    )

    # Profile-aware workspace directory
    profile = (env.get("OPENCLAW_PROFILE") or "").strip()
    ws_name = (
        f"workspace-{profile}"
        if profile and profile.lower() != "default"
        else "workspace"
    )
    workspace_dir = state_dir / ws_name

    # All candidate skill source dirs (ascending precedence)
    all_sources: list[tuple[SkillSource, Path]] = []

    # bundled: lowest precedence, only if found
    bundled = resolve_bundled_skills_dir(env)
    if bundled is not None:
        all_sources.append(("bundled", bundled))

    all_sources.extend([
        ("managed", state_dir / "skills"),
        ("personal-agents", home / ".agents" / "skills"),
        (
            "project-agents",
            workspace_dir / ".agents" / "skills",
        ),
        ("workspace", workspace_dir / "skills"),
    ])

    # Keep only dirs that actually exist
    skill_sources = [
        SkillSourceDir(source=src, dir=d)
        for src, d in all_sources
        if d.is_dir()
    ]

    return OpenClawPaths(
        state_dir=state_dir,
        workspace_dir=workspace_dir,
        config_file=state_dir / "openclaw.json",
        skill_sources=skill_sources,
    )


def resolve_bundled_skills_dir(
    env: Optional[dict[str, str]] = None,
) -> Optional[Path]:
    r"""Locate the openclaw package's bundled skills dir.

    Strategy (in order):
      1. ``$OPENCLAW_BUNDLED_SKILLS_DIR`` env override
      2. Walk up from the ``openclaw`` binary realpath
      3. ``npm root -g`` fallback

    Args:
        env: Environment mapping. Defaults to ``os.environ``.

    Returns:
        Path to the bundled skills directory, or *None*.
    """
    if env is None:
        env = dict(os.environ)

    # 1. env override
    override = (
        env.get("OPENCLAW_BUNDLED_SKILLS_DIR", "") or ""
    ).strip()
    if override:
        p = Path(override)
        if p.exists():
            return p

    # 2. walk up from openclaw binary realpath
    bin_path = shutil.which("openclaw")
    if bin_path:
        try:
            real = Path(bin_path).resolve()
            cur = real.parent
            for _ in range(5):
                candidate = cur / "skills"
                pkg_json = cur / "package.json"
                if candidate.exists() and pkg_json.exists():
                    return candidate
                parent = cur.parent
                if parent == cur:
                    break
                cur = parent
        except OSError:
            pass

    # 3. npm root -g
    try:
        result = subprocess.run(
            ["npm", "root", "-g"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        npm_global = result.stdout.strip()
        if npm_global:
            candidate = Path(npm_global) / "openclaw" / "skills"
            if candidate.exists():
                return candidate
    except (OSError, subprocess.TimeoutExpired):
        pass

    return None
