#!/usr/bin/env python3
"""Validate a proposed skill update and update its candidate status."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from learning_store import (
    default_home,
    load_json,
    utc_now,
    write_json,
)
from provider_roots import find_skill


def validate_structure(skill_path: Path) -> list[str]:
    failures: list[str] = []
    skill_file = skill_path / "SKILL.md"
    if not skill_file.is_file():
        return [f"missing SKILL.md: {skill_file}"]

    text = skill_file.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        failures.append("SKILL.md must start with YAML frontmatter")
    if "\n---\n" not in text[4:]:
        failures.append("SKILL.md frontmatter is not closed")
    if "name:" not in text.split("\n---\n", 1)[0]:
        failures.append("SKILL.md frontmatter is missing name")
    if "description:" not in text.split("\n---\n", 1)[0]:
        failures.append("SKILL.md frontmatter is missing description")
    if "[TODO" in text:
        failures.append("SKILL.md contains an unfinished TODO placeholder")
    return failures


def validate_candidate_schema(candidate: dict[str, object]) -> list[str]:
    failures: list[str] = []
    required = ["target_skill", "risk", "changes", "validation_commands"]
    for key in required:
        if key not in candidate:
            failures.append(f"candidate is missing required field: {key}")

    risk = candidate.get("risk")
    if risk not in {"low", "medium", "high"}:
        failures.append("candidate risk must be low, medium, or high")

    changes = candidate.get("changes")
    if not isinstance(changes, list) or not changes:
        failures.append("candidate changes must be a non-empty array")
    else:
        for index, change in enumerate(changes, 1):
            if not isinstance(change, dict):
                failures.append(f"change {index} must be an object")
                continue
            for key in ("file", "type", "summary"):
                if not change.get(key):
                    failures.append(f"change {index} is missing {key}")
            if change.get("type") not in {"add", "update", "delete"}:
                failures.append(
                    f"change {index} type must be add, update, or delete"
                )

    commands = candidate.get("validation_commands")
    if not isinstance(commands, list):
        failures.append("candidate validation_commands must be an array")

    return failures


def run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout: float,
) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-8000:],
            "stderr": completed.stderr[-8000:],
            "passed": completed.returncode == 0,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": command,
            "returncode": None,
            "stdout": (error.stdout or "")[-8000:] if error.stdout else "",
            "stderr": f"timed out after {timeout}s",
            "passed": False,
        }


def quick_validate_command() -> tuple[list[str], Path] | None:
    script = (
        Path.home()
        / ".codex"
        / "skills"
        / ".system"
        / "skill-creator"
        / "scripts"
        / "quick_validate.py"
    )
    if not script.is_file():
        return None
    return [sys.executable, str(script)], script


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=default_home())
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--skill-path", type=Path)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=float, default=300.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidate_path = args.home / "candidates" / f"{args.candidate}.json"
    if not candidate_path.is_file():
        raise SystemExit(f"candidate not found: {candidate_path}")

    candidate = load_json(candidate_path)
    failures = validate_candidate_schema(candidate)
    target_skill = str(candidate.get("target_skill") or "")
    if args.skill_path:
        skill_path = args.skill_path.resolve()
    elif target_skill:
        skill_path = find_skill(target_skill)
    else:
        skill_path = None

    if skill_path is None:
        failures.append(
            "target skill is missing or not installed: "
            f"{target_skill or '<unknown>'}"
        )

    command_results: list[dict[str, object]] = []
    warnings: list[str] = []

    if skill_path is not None:
        failures.extend(validate_structure(skill_path))

    snapshot_path = candidate.get("snapshot_path")
    if snapshot_path:
        if not Path(str(snapshot_path)).exists():
            failures.append(f"snapshot path does not exist: {snapshot_path}")
    else:
        warnings.append("candidate has no snapshot_path")
        if candidate.get("risk") == "high":
            failures.append("high-risk candidate requires a snapshot")

    validation_commands = candidate.get("validation_commands", [])
    if not isinstance(validation_commands, list):
        validation_commands = []

    for raw_command in validation_commands:
        if not isinstance(raw_command, list) or not all(
            isinstance(part, str) for part in raw_command
        ):
            failures.append(f"invalid validation command: {raw_command!r}")
            continue
        result = run_command(
            raw_command,
            cwd=args.cwd,
            timeout=args.timeout,
        )
        command_results.append(result)
        if not result["passed"]:
            failures.append(f"validation command failed: {raw_command!r}")

    if skill_path is not None:
        quick_validate = quick_validate_command()
        if quick_validate is None:
            warnings.append("official quick_validate.py was not found")
        else:
            command, _ = quick_validate
            result = run_command(
                command + [str(skill_path)],
                cwd=args.cwd,
                timeout=args.timeout,
            )
            command_results.append(result)
            if not result["passed"]:
                failures.append("official quick_validate.py failed")

    status = "validated" if not failures else "validation_failed"
    report = {
        "candidate_id": args.candidate,
        "target_skill": target_skill,
        "skill_path": str(skill_path) if skill_path is not None else "",
        "validated_at": utc_now(),
        "status": status,
        "failures": failures,
        "warnings": warnings,
        "commands": command_results,
    }
    report_path = args.home / "reports" / f"{args.candidate}-validation.json"
    write_json(report_path, report)

    candidate["status"] = status
    candidate["validation_report"] = str(report_path)
    candidate["validated_at"] = report["validated_at"]
    write_json(candidate_path, candidate)

    print(json.dumps(report, ensure_ascii=True, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
