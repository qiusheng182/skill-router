#!/usr/bin/env python3
"""Small regression suite for the skill-router administrator tools."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import learning_store
import provider_roots
import validate_candidate
import context_budget
import skill_context
import experience_store
import practice_runner


def test_provider_roots_honor_env_override() -> None:
    temp_root = Path(tempfile.mkdtemp()) / "custom-skills"
    old_value = os.environ.get("CODEX_SKILLS_PATH")
    os.environ["CODEX_SKILLS_PATH"] = str(temp_root)
    try:
        roots = provider_roots.provider_roots()
        assert roots["codex"] == temp_root
        assert {"claude", "opencode", "cursor", "gemini", "windsurf"} <= set(roots)
    finally:
        if old_value is None:
            os.environ.pop("CODEX_SKILLS_PATH", None)
        else:
            os.environ["CODEX_SKILLS_PATH"] = old_value


def test_source_domain_policy() -> None:
    policy = {
        "research": {
            "allowed_domains": ["rfc-editor.org"],
            "max_sources": 5,
        }
    }
    learning_store.validate_source_urls(
        ["https://www.rfc-editor.org/rfc/rfc9110.html"],
        policy,
    )
    try:
        learning_store.validate_source_urls(
            ["https://example.com/post"],
            policy,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("disallowed source domain was not rejected")


def test_change_object_validation() -> None:
    learning_store.validate_change_object(
        {"file": "SKILL.md", "type": "update", "summary": "fix"},
        1,
    )
    try:
        learning_store.validate_change_object({"file": "SKILL.md"}, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete change object was not rejected")


def test_validate_structure_handles_crlf() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        skill = Path(tmp) / "skill"
        skill.mkdir()
        (skill / "SKILL.md").write_bytes(
            b"---\r\nname: demo\r\ndescription: demo\r\n---\r\n# Demo\r\n"
        )
        failures = validate_candidate.validate_structure(skill)
        assert failures == [], failures


def test_context_budget_toggle_preserves_frontmatter() -> None:
    text = "---\nname: demo\ndescription: demo\n---\n# Demo\n"
    disabled, changed = context_budget.set_disable_flag(text, True)
    assert changed
    assert "disable-model-invocation: true" in disabled
    enabled, changed = context_budget.set_disable_flag(disabled, False)
    assert changed
    assert "disable-model-invocation" not in enabled
    assert enabled == text


def test_context_pack_selects_relevant_section() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        skill = Path(tmp) / "demo"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n"
            "## Overview\n\nGeneral information.\n\n"
            "## PDF Workflow\n\nUse PDF tools.\n\n"
            "## Unrelated\n\nNothing here.\n",
            encoding="utf-8",
        )
        pack = skill_context.render_pack(skill, "pdf workflow", 120, set())
        assert "PDF Workflow" in pack
        assert "Unrelated" in pack
        assert "Omitted Sections" in pack


def test_experience_metric_parsing() -> None:
    metrics = experience_store.parse_metric(
        ["tokens=1200", "duration_s=4.5", "label=stable"]
    )
    assert metrics == {
        "tokens": 1200,
        "duration_s": 4.5,
        "label": "stable",
    }


def test_practice_suite_validation() -> None:
    cases = practice_runner.validate_suite(
        {
            "cases": [
                {
                    "id": "ok",
                    "command": ["python", "-c", "print('ok')"],
                }
            ]
        }
    )
    assert len(cases) == 1


def main() -> None:
    tests = [
        test_provider_roots_honor_env_override,
        test_source_domain_policy,
        test_change_object_validation,
        test_validate_structure_handles_crlf,
        test_context_budget_toggle_preserves_frontmatter,
        test_context_pack_selects_relevant_section,
        test_experience_metric_parsing,
        test_practice_suite_validation,
    ]
    for test in tests:
        test()
        print(f"ok: {test.__name__}")


if __name__ == "__main__":
    main()
