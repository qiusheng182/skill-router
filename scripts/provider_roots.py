#!/usr/bin/env python3
"""Shared provider-root discovery for the skill-router administrator tools."""

from __future__ import annotations

import os
from pathlib import Path


_PROVIDER_SPECS = {
    "codex": ("CODEX_SKILLS_PATH", ".codex", "skills"),
    "opencode": ("OPENCODE_SKILLS_PATH", ".config", "opencode", "skills"),
    "claude": ("CLAUDE_SKILLS_PATH", ".claude", "skills"),
    "cursor": ("CURSOR_SKILLS_PATH", ".cursor", "skills"),
    "gemini": ("GEMINI_SKILLS_PATH", ".gemini", "skills"),
    "windsurf": ("WINDSURF_SKILLS_PATH", ".windsurf", "skills"),
}


def provider_roots() -> dict[str, Path]:
    """Return canonical provider roots, honoring provider-specific env vars."""
    home = Path.home()
    roots: dict[str, Path] = {}
    for name, spec in _PROVIDER_SPECS.items():
        env_name = spec[0]
        default_path = home.joinpath(*spec[1:])
        roots[name] = Path(os.environ.get(env_name, default_path))
    return roots


def parse_custom_roots(values: list[str] | None) -> dict[str, Path]:
    """Parse ``name=path`` entries into lowercase provider names."""
    roots: dict[str, Path] = {}
    for value in values or []:
        name, separator, path = value.partition("=")
        if not separator or not name.strip() or not path.strip():
            raise ValueError(f"invalid custom root: {value}")
        roots[name.strip().lower()] = Path(path.strip())
    return roots


def find_skill(
    skill_name: str,
    roots: dict[str, Path] | None = None,
) -> Path | None:
    """Find the first installed root containing a named skill."""
    search_roots = roots if roots is not None else provider_roots()
    for root in search_roots.values():
        candidate = root / skill_name
        if (candidate / "SKILL.md").is_file():
            return candidate
    return None
