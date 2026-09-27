#!/usr/bin/env python3
"""Record skill learnings and update candidates."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_POLICY: dict[str, Any] = {
    "schema_version": 1,
    "mode": "propose",
    "minimum_failed_attempts": 2,
    "research": {
        "enabled": True,
        "official_sources_only": True,
        "max_sources": 5,
        "allowed_domains": [],
    },
    "apply": {
        "require_validation": True,
        "create_snapshot": True,
        "allow_deletions": False,
        "allow_permission_changes": False,
        "allow_new_scripts": False,
    },
    "sync_providers": ["codex", "opencode"],
    "review": {
        "pending_on_high_risk": True,
        "pending_on_unverified_source": True,
        "pending_on_frontmatter_change": True,
    },
}


def default_home() -> Path:
    configured = os.environ.get("SKILL_EVOLUTION_HOME")
    return Path(configured) if configured else Path.home() / ".codex" / "skill-evolution"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6]}"


def ensure_home(home: Path) -> None:
    for child in (
        "records",
        "candidates",
        "snapshots",
        "reports",
        "experiences",
        "practice-reports",
    ):
        (home / child).mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_policy(home: Path) -> tuple[dict[str, Any], bool]:
    path = home / "policy.json"
    if not path.exists():
        return dict(DEFAULT_POLICY), False
    return load_json(path), True


def parse_json_argument(value: str, label: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid {label} JSON: {error}") from error


def validate_change_object(change: Any, index: int) -> None:
    if not isinstance(change, dict):
        raise ValueError(f"change {index} must be a JSON object")
    for key in ("file", "type", "summary"):
        if not change.get(key):
            raise ValueError(f"change {index} is missing {key}")
    if change["type"] not in {"add", "update", "delete"}:
        raise ValueError(
            f"change {index} type must be add, update, or delete"
        )


def validate_source_urls(urls: list[str], policy: dict[str, Any]) -> None:
    research_policy = policy.get("research", {})
    allowed_domains = {
        str(domain).lower()
        for domain in research_policy.get("allowed_domains", [])
    }
    max_sources = int(research_policy.get("max_sources", len(urls) or 5))
    if len(urls) > max_sources:
        raise ValueError(
            f"too many sources: got {len(urls)}, max is {max_sources}"
        )

    if not allowed_domains:
        return

    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        if not host:
            raise ValueError(f"source URL has no hostname: {url}")
        host_without_www = host[4:] if host.startswith("www.") else host
        if not any(
            host_without_www == domain
            or host_without_www.endswith(f".{domain}")
            for domain in allowed_domains
        ):
            raise ValueError(
                f"source domain is not allowed by policy: {host} "
                f"({url})"
            )


def command_record(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    policy, _ = load_policy(args.home)
    source_urls = list(args.source or [])
    validate_source_urls(source_urls, policy)
    failed = list(args.failed_attempt or [])
    successful = list(args.successful_attempt or [])
    if not failed and not successful:
        raise ValueError("at least one failed or successful attempt is required")

    attempts: list[dict[str, Any]] = []
    sequence = 1
    for action in failed:
        attempts.append(
            {"sequence": sequence, "stage": "failed", "action": action}
        )
        sequence += 1
    for action in successful:
        attempts.append(
            {"sequence": sequence, "stage": "successful", "action": action}
        )
        sequence += 1

    record_id = make_id("LR")
    record = {
        "id": record_id,
        "created_at": utc_now(),
        "task": args.task,
        "target_skill": args.target_skill,
        "attempts": attempts,
        "solution": args.solution,
        "evidence": list(args.evidence or []),
        "source_urls": source_urls,
        "generalizability": args.generalizability,
        "status": "recorded",
    }
    path = args.home / "records" / f"{record_id}.json"
    write_json(path, record)
    print(json.dumps({"id": record_id, "path": str(path)}, ensure_ascii=True))


def command_candidate(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    record_path = args.home / "records" / f"{args.record}.json"
    if not record_path.is_file():
        raise ValueError(f"learning record not found: {args.record}")
    record = load_json(record_path)

    changes = [
        parse_json_argument(value, "change")
        for value in (args.change_json or [])
    ]
    if not changes:
        raise ValueError("at least one --change-json is required")
    for index, change in enumerate(changes, 1):
        validate_change_object(change, index)

    validation_commands = [
        parse_json_argument(value, "validation command")
        for value in (args.validation_command_json or [])
    ]
    for index, command in enumerate(validation_commands, 1):
        if not isinstance(command, list) or not command or not all(
            isinstance(part, str) for part in command
        ):
            raise ValueError(
                f"validation command {index} must be a non-empty JSON string array"
            )

    candidate_id = make_id("UC")
    candidate = {
        "id": candidate_id,
        "record_id": args.record,
        "created_at": utc_now(),
        "target_skill": args.target_skill,
        "risk": args.risk,
        "changes": changes,
        "validation_commands": validation_commands,
        "expected_result": args.expected_result,
        "snapshot_path": args.snapshot,
        "status": "proposed",
        "record_task": record.get("task"),
    }
    path = args.home / "candidates" / f"{candidate_id}.json"
    write_json(path, candidate)
    print(json.dumps({"id": candidate_id, "path": str(path)}, ensure_ascii=True))


def command_list(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    directory = args.home / ("records" if args.kind == "records" else "candidates")
    values = [load_json(path) for path in sorted(directory.glob("*.json"))]
    if args.brief:
        brief_values = []
        for value in values:
            brief_values.append(
                {
                    "id": value.get("id"),
                    "created_at": value.get("created_at"),
                    "task": value.get("task") or value.get("record_task"),
                    "target_skill": value.get("target_skill"),
                    "status": value.get("status"),
                }
            )
        print(json.dumps(brief_values, ensure_ascii=True, indent=2))
        return
    print(json.dumps(values, ensure_ascii=True, indent=2))


def command_show(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    for directory in ("records", "candidates"):
        path = args.home / directory / f"{args.id}.json"
        if path.is_file():
            print(json.dumps(load_json(path), ensure_ascii=True, indent=2))
            return
    raise ValueError(f"learning artifact not found: {args.id}")


def command_snapshot(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    source = args.skill_path.resolve()
    if not (source / "SKILL.md").is_file():
        raise ValueError(f"skill path does not contain SKILL.md: {source}")
    destination = (
        args.home
        / "snapshots"
        / source.name
        / f"{utc_now().replace(':', '').replace('+', '_')}-{args.label}"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    print(
        json.dumps(
            {
                "skill": source.name,
                "snapshot": str(destination),
                "created_at": utc_now(),
            },
            ensure_ascii=True,
        )
    )


def command_policy(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    path = args.home / "policy.json"
    if args.set_mode:
        policy, _ = load_policy(args.home)
        policy["mode"] = args.set_mode
        write_json(path, policy)
    elif not path.exists():
        write_json(path, DEFAULT_POLICY)

    policy = load_json(path)
    print(
        json.dumps(
            {"path": str(path), "policy": policy},
            ensure_ascii=True,
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=default_home())
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record")
    record.add_argument("--task", required=True)
    record.add_argument("--target-skill", required=True)
    record.add_argument("--failed-attempt", action="append")
    record.add_argument("--successful-attempt", action="append")
    record.add_argument("--solution", required=True)
    record.add_argument("--evidence", action="append")
    record.add_argument("--source", action="append")
    record.add_argument(
        "--generalizability",
        choices=("one_off", "pattern", "principle"),
        required=True,
    )
    record.set_defaults(func=command_record)

    candidate = subparsers.add_parser("candidate")
    candidate.add_argument("--record", required=True)
    candidate.add_argument("--target-skill", required=True)
    candidate.add_argument("--change-json", action="append")
    candidate.add_argument("--validation-command-json", action="append")
    candidate.add_argument(
        "--risk",
        choices=("low", "medium", "high"),
        default="medium",
    )
    candidate.add_argument("--expected-result", required=True)
    candidate.add_argument("--snapshot")
    candidate.set_defaults(func=command_candidate)

    listing = subparsers.add_parser("list")
    listing.add_argument(
        "--kind",
        choices=("records", "candidates"),
        default="records",
    )
    listing.add_argument("--brief", action="store_true")
    listing.set_defaults(func=command_list)

    show = subparsers.add_parser("show")
    show.add_argument("--id", required=True)
    show.set_defaults(func=command_show)

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--skill-path", required=True, type=Path)
    snapshot.add_argument("--label", required=True)
    snapshot.set_defaults(func=command_snapshot)

    policy = subparsers.add_parser("policy")
    policy.add_argument(
        "--set-mode",
        choices=("observe", "propose", "auto_apply_local", "auto_sync"),
    )
    policy.set_defaults(func=command_policy)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: {error}")


if __name__ == "__main__":
    main()
