r"""Safely extract a config fragment from openclaw.json.

Only exports non-secret fields:
  - ``agents.defaults`` (model, thinking prefs — no creds)
  - ``agents.list[].skills`` (allow-list per agent)
  - ``skills.allowBundled``
  - ``skills.limits``

Explicitly **never** exports: credentials, env, oauth,
channel tokens, gateway settings, secrets paths, or any
key whose name contains "secret", "token", "key",
"password", "auth", or "credential".
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ── Pydantic models ──────────────────────────────────────

class AgentDefaults(BaseModel):
    r"""Safe subset of ``agents.defaults``.

    Attributes:
        model (Optional[str]): Default model name.
        thinking_default (Optional[str]): Thinking pref.
        thinking_budget (Optional[int]): Budget for
            thinking tokens.
        max_tokens (Optional[int]): Max output tokens.
        skills (Optional[List[str]]): Default skill list.
    """

    model: Optional[str] = None
    thinking_default: Optional[str] = Field(
        default=None, alias="thinkingDefault",
    )
    thinking_budget: Optional[int] = Field(
        default=None, alias="thinkingBudget",
    )
    max_tokens: Optional[int] = Field(
        default=None, alias="maxTokens",
    )
    skills: Optional[List[str]] = None

    model_config = {"populate_by_name": True}


class AgentSkills(BaseModel):
    r"""Safe subset of a single agent entry.

    Attributes:
        id (str): The agent identifier.
        skills (Optional[List[str]]): Skill slugs allowed
            for this agent.
    """

    id: str = ""
    skills: Optional[List[str]] = None

    model_config = {"populate_by_name": True}


class SkillsLimits(BaseModel):
    r"""Safe subset of ``skills.limits``.

    Attributes:
        max_skills_loaded_per_source (Optional[int]):
            Per-source limit.
        max_skills_in_prompt (Optional[int]):
            How many skills to include in prompt.
        max_skills_prompt_chars (Optional[int]):
            Character budget for skills in prompt.
        max_skill_file_bytes (Optional[int]):
            Max bytes per skill file.
    """

    max_skills_loaded_per_source: Optional[int] = Field(
        default=None,
        alias="maxSkillsLoadedPerSource",
    )
    max_skills_in_prompt: Optional[int] = Field(
        default=None,
        alias="maxSkillsInPrompt",
    )
    max_skills_prompt_chars: Optional[int] = Field(
        default=None,
        alias="maxSkillsPromptChars",
    )
    max_skill_file_bytes: Optional[int] = Field(
        default=None,
        alias="maxSkillFileBytes",
    )

    model_config = {"populate_by_name": True}


class ConfigFragment(BaseModel):
    r"""Safe, non-secret subset of openclaw.json.

    Attributes:
        agents (Optional[dict]): Agent defaults and
            per-agent skill lists.
        skills (Optional[dict]): Bundled-skills flag
            and limit settings.
    """

    agents: Optional[Dict[str, Any]] = None
    skills: Optional[Dict[str, Any]] = None


# ── Implementation ───────────────────────────────────────

def extract_config_fragment(
    config_file_path: Path,
) -> Optional[ConfigFragment]:
    r"""Load openclaw.json and extract safe, non-secret fields.

    Uses explicit whitelisting — only known-safe keys are
    ever included.

    Args:
        config_file_path: Path to ``openclaw.json``.

    Returns:
        A ``ConfigFragment`` with safe data, or *None* if
        the file doesn't exist or has no safe content.

    Raises:
        RuntimeError: If the file exists but can't be read
            or parsed.
    """
    try:
        text = config_file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RuntimeError(
            f"Failed to read config at {config_file_path}: "
            f"{exc}"
        ) from exc

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON in {config_file_path}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        return None

    fragment_data: Dict[str, Any] = {}

    # ── agents.defaults ──────────────────────────────
    agents_raw = raw.get("agents")
    if isinstance(agents_raw, dict):
        agents_section: Dict[str, Any] = {}

        defaults_raw = agents_raw.get("defaults")
        if defaults_raw is not None:
            try:
                parsed = AgentDefaults.model_validate(
                    defaults_raw
                )
                defaults_dict = parsed.model_dump(
                    by_alias=True,
                    exclude_none=True,
                )
                if defaults_dict:
                    agents_section["defaults"] = (
                        defaults_dict
                    )
            except Exception:
                pass

        # ── agents.list[].skills ─────────────────────
        agent_list = agents_raw.get("list")
        if isinstance(agent_list, list):
            safe_list: List[Dict[str, Any]] = []
            for item in agent_list:
                if not isinstance(item, dict):
                    continue
                agent_id = item.get("id", "")
                if not isinstance(agent_id, str) or not agent_id:
                    continue
                entry: Dict[str, Any] = {"id": agent_id}
                skills_val = item.get("skills")
                if isinstance(skills_val, list):
                    entry["skills"] = [
                        s for s in skills_val
                        if isinstance(s, str)
                    ]
                safe_list.append(entry)
            if safe_list:
                agents_section["list"] = safe_list

        if agents_section:
            fragment_data["agents"] = agents_section

    # ── skills.allowBundled + skills.limits ──────────
    skills_raw = raw.get("skills")
    if isinstance(skills_raw, dict):
        skills_section: Dict[str, Any] = {}

        allow_bundled = skills_raw.get("allowBundled")
        if isinstance(allow_bundled, bool):
            skills_section["allowBundled"] = allow_bundled

        limits_raw = skills_raw.get("limits")
        if limits_raw is not None:
            try:
                parsed_limits = (
                    SkillsLimits.model_validate(limits_raw)
                )
                limits_dict = parsed_limits.model_dump(
                    by_alias=True,
                    exclude_none=True,
                )
                if limits_dict:
                    skills_section["limits"] = limits_dict
            except Exception:
                pass

        if skills_section:
            fragment_data["skills"] = skills_section

    if not fragment_data:
        return None

    return ConfigFragment(**fragment_data)


async def async_extract_config_fragment(
    config_file_path: Path,
) -> Optional[ConfigFragment]:
    r"""Async wrapper for ``extract_config_fragment``.

    Runs the sync function in a thread pool to avoid
    blocking the event loop.

    Args:
        config_file_path: Path to ``openclaw.json``.

    Returns:
        A ``ConfigFragment`` or *None*.
    """
    return await asyncio.to_thread(
        extract_config_fragment, config_file_path
    )
