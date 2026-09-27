#!/usr/bin/env python3
"""Apply a validated skill update candidate with snapshot and policy checks."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from learning_store import (
    ensure_home,
    load_json,
    load_policy,
    utc_now,
    write_json,
)
from provider_roots import find_skill


def ensure_within_skill(target: Path, skill_path: Path) -> None:
    resolved_skill = skill_path.resolve()
    resolved_target = target.resolve()
    if resolved_skill != resolved_target and resolved_skill not in resolved_target.parents:
        raise ValueError(f"target is outside the skill: {target}")


def preflight_changes(candidate: dict[str, Any], skill_path: Path) -> None:
    changes = candidate.get("changes", [])
    if not isinstance(changes, list) or not changes:
        raise ValueError("candidate has no changes to apply")

    for index, change in enumerate(changes, 1):
        if not isinstance(change, dict):
            raise ValueError(f"change {index} must be an object")
        file_value = str(change.get("file") or "")
        change_type = change.get("type")
        if not file_value:
            raise ValueError(f"change {index} is missing file")
        if change_type not in {"add", "update", "delete"}:
            raise ValueError(f"change {index} has invalid type")

        target = skill_path / file_value
        ensure_within_skill(target, skill_path)

        if change_type in {"add", "update"}:
            content = change.get("content")
            if content is None:
                raise ValueError(
                    f"change {index} requires string content for {change_type}"
                )
            if not isinstance(content, str):
                raise ValueError(f"change {index} content must be a string")

        if change_type == "add" and target.exists():
            raise ValueError(f"change {index} would overwrite existing file: {file_value}")
        if change_type in {"update", "delete"} and not target.exists():
            raise ValueError(f"change {index} target does not exist: {file_value}")


def policy_violations(
    candidate: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    violations: list[str] = []
    apply_policy = policy.get("apply", {})
    review_policy = policy.get("review", {})

    for index, change in enumerate(candidate.get("changes", []), 1):
        change_type = change.get("type")
        file_value = str(change.get("file") or "")

        if change_type == "delete" and not apply_policy.get("allow_deletions"):
            violations.append(
                f"change {index} deletes a file but policy disallows deletions"
            )

        if (
            change_type == "add"
            and file_value.startswith("scripts/")
            and not apply_policy.get("allow_new_scripts")
        ):
            violations.append(
                f"change {index} adds a script but policy disallows new scripts"
            )

        if change.get("permission_change") and not apply_policy.get(
            "allow_permission_changes"
        ):
            violations.append(
                f"change {index} changes permissions but policy disallows it"
            )

        if file_value == "SKILL.md" and review_policy.get(
            "pending_on_frontmatter_change", True
        ):
            violations.append(
                f"change {index} touches SKILL.md and policy requires approval"
            )

    return violations


def make_snapshot(
    skill_path: Path,
    home: Path,
    candidate_id: str,
) -> Path:
    stamp = utc_now().replace(":", "").replace("+", "_")
    destination = (
        home
        / "snapshots"
        / skill_path.name
        / f"{stamp}-apply-{candidate_id}"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        skill_path,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return destination


def apply_changes(
    candidate: dict[str, Any],
    skill_path: Path,
    *,
    dry_run: bool,
) -> list[dict[str, str]]:
    applied: list[dict[str, str]] = []
    for index, change in enumerate(candidate.get("changes", []), 1):
        file_value = str(change["file"])
        change_type = change["type"]
        target = skill_path / file_value

        action = f"{change_type} {file_value}"
        if dry_run:
            applied.append({"index": str(index), "action": action})
            continue

        if change_type == "add":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(change["content"]), encoding="utf-8")
        elif change_type == "update":
            target.write_text(str(change["content"]), encoding="utf-8")
        elif change_type == "delete":
            target.unlink()

        applied.append({"index": str(index), "action": action})

    return applied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home() / ".codex" / "skill-evolution")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--skill-path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_home(args.home)

    candidate_path = args.home / "candidates" / f"{args.candidate}.json"
    if not candidate_path.is_file():
        raise SystemExit(f"candidate not found: {candidate_path}")

    candidate = load_json(candidate_path)
    policy, _ = load_policy(args.home)
    target_skill = str(candidate.get("target_skill") or "")
    skill_path = (
        args.skill_path.resolve()
        if args.skill_path
        else find_skill(target_skill)
    )
    if skill_path is None:
        raise SystemExit(f"target skill is not installed: {target_skill or '<unknown>'}")

    preflight_changes(candidate, skill_path)
    violations = policy_violations(candidate, policy)

    if candidate.get("status") != "validated" and not args.force:
        violations.append(
            f"candidate status is {candidate.get('status')!r}; run validation first "
            "or use --force"
        )
    if candidate.get("risk") == "high" and not candidate.get("snapshot_path"):
        violations.append("high-risk candidate requires a snapshot_path")

    if violations and not args.force:
        report = {
            "candidate_id": args.candidate,
            "target_skill": target_skill,
            "skill_path": str(skill_path),
            "checked_at": utc_now(),
            "status": "blocked",
            "violations": violations,
        }
        report_path = args.home / "reports" / f"{args.candidate}-apply.json"
        write_json(report_path, report)
        print(json.dumps(report, ensure_ascii=True, indent=2))
        raise SystemExit(1)

    if args.dry_run:
        planned = apply_changes(candidate, skill_path, dry_run=True)
        print(
            json.dumps(
                {
                    "candidate_id": args.candidate,
                    "target_skill": target_skill,
                    "skill_path": str(skill_path),
                    "status": "dry_run",
                    "planned_changes": planned,
                    "overridden_violations": violations if args.force else [],
                },
                ensure_ascii=True,
                indent=2,
            )
        )
        return

    snapshot_path = candidate.get("snapshot_path")
    snapshot = Path(str(snapshot_path)) if snapshot_path else None
    if snapshot is None or not snapshot.exists():
        snapshot = make_snapshot(skill_path, args.home, args.candidate)

    applied = apply_changes(candidate, skill_path, dry_run=False)
    report = {
        "candidate_id": args.candidate,
        "target_skill": target_skill,
        "skill_path": str(skill_path),
        "applied_at": utc_now(),
        "status": "applied",
        "snapshot": str(snapshot),
        "changes": applied,
        "overridden_violations": violations if args.force else [],
    }
    report_path = args.home / "reports" / f"{args.candidate}-apply.json"
    write_json(report_path, report)

    candidate["status"] = "applied"
    candidate["applied_at"] = report["applied_at"]
    candidate["apply_report"] = str(report_path)
    candidate["snapshot_path"] = str(snapshot)
    write_json(candidate_path, candidate)

    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
