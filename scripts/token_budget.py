#!/usr/bin/env python3
"""Report and reduce always-loaded skill metadata context."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from provider_roots import provider_roots


DISABLE_KEY = "disable-model-invocation"


def state_home() -> Path:
    import os

    configured = os.environ.get("SKILL_EVOLUTION_HOME")
    return Path(configured) if configured else Path.home() / ".codex" / "skill-evolution"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def read_frontmatter(path: Path) -> tuple[list[str], int, int]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return [], -1, -1
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines, 0, index
    return lines, 0, -1


def frontmatter_value(lines: list[str], start: int, end: int, key: str) -> str:
    if start < 0 or end < 0:
        return ""
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.*?)\s*$")
    for line in lines[start + 1 : end]:
        match = pattern.match(line.rstrip("\r\n"))
        if match:
            return match.group(1).strip().strip("\"'")
    return ""


def skill_entries(provider: str, root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not root.is_dir():
        return entries

    for skill_dir in sorted(root.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_dir.is_dir() or not skill_file.is_file():
            continue
        lines, start, end = read_frontmatter(skill_file)
        name = frontmatter_value(lines, start, end, "name") or skill_dir.name
        description = frontmatter_value(lines, start, end, "description")
        disabled = frontmatter_value(
            lines,
            start,
            end,
            DISABLE_KEY,
        ).lower() in {"true", "1", "yes"}
        entries.append(
            {
                "provider": provider,
                "name": name,
                "folder": skill_dir.name,
                "description": description,
                "description_chars": len(description),
                "approximate_tokens": round(len(description) / 4),
                "disabled": disabled,
                "path": str(skill_file.resolve()),
                "root": str(root.resolve()),
            }
        )
    return entries


def scan(providers: list[str]) -> list[dict[str, Any]]:
    roots = provider_roots()
    unknown = sorted(set(providers) - set(roots))
    if unknown:
        raise ValueError(f"unknown providers: {', '.join(unknown)}")
    entries: list[dict[str, Any]] = []
    for provider in providers:
        entries.extend(skill_entries(provider, roots[provider]))
    return entries


def set_disabled(content: str, disabled: bool) -> str:
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")

    closing = -1
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing = index
            break
    if closing < 0:
        raise ValueError("SKILL.md frontmatter is not closed")

    pattern = re.compile(rf"^\s*{re.escape(DISABLE_KEY)}\s*:")
    existing = [index for index, line in enumerate(lines[1:closing], 1) if pattern.match(line)]
    newline = "\r\n" if lines[closing].endswith("\r\n") else "\n"

    if disabled:
        if existing:
            for index in existing:
                lines[index] = f"{DISABLE_KEY}: true{newline}"
        else:
            lines.insert(closing, f"{DISABLE_KEY}: true{newline}")
    else:
        for index in reversed(existing):
            del lines[index]

    return "".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=state_home())
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report")
    report.add_argument("--providers", default="codex")
    report.add_argument("--top", type=int, default=15)

    apply = subparsers.add_parser("apply")
    apply.add_argument("--providers", default="codex")
    apply.add_argument("--keep", default="skill-router")
    apply.add_argument("--profile")
    apply.add_argument("--apply", action="store_true")

    restore = subparsers.add_parser("restore")
    restore.add_argument("--profile", required=True)
    restore.add_argument("--apply", action="store_true")

    listing = subparsers.add_parser("list-profiles")
    listing.set_defaults(func=list_profiles)
    return parser


def parse_providers(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def command_report(args: argparse.Namespace) -> None:
    entries = scan(parse_providers(args.providers))
    enabled = [entry for entry in entries if not entry["disabled"]]
    disabled = [entry for entry in entries if entry["disabled"]]
    top = sorted(
        enabled,
        key=lambda entry: entry["description_chars"],
        reverse=True,
    )[: max(0, args.top)]
    report = {
        "providers": parse_providers(args.providers),
        "skills": len(entries),
        "enabled": len(enabled),
        "disabled": len(disabled),
        "enabled_description_chars": sum(
            entry["description_chars"] for entry in enabled
        ),
        "enabled_approximate_tokens": sum(
            entry["approximate_tokens"] for entry in enabled
        ),
        "top_enabled_by_description": [
            {
                "name": entry["name"],
                "provider": entry["provider"],
                "description_chars": entry["description_chars"],
                "approximate_tokens": entry["approximate_tokens"],
            }
            for entry in top
        ],
    }
    print(json.dumps(report, ensure_ascii=True, indent=2))


def command_apply(args: argparse.Namespace) -> None:
    providers = parse_providers(args.providers)
    keep = {item.strip().lower() for item in args.keep.split(",") if item.strip()}
    entries = scan(providers)
    profile_id = args.profile or f"profile-{utc_stamp()}"
    profile_dir = args.home / "profiles" / profile_id
    changes: list[dict[str, Any]] = []

    for entry in entries:
        skill_path = Path(entry["path"])
        should_disable = entry["folder"].lower() not in keep
        if entry["disabled"] == should_disable:
            continue
        original = skill_path.read_text(encoding="utf-8")
        updated = set_disabled(original, should_disable)
        if updated == original:
            continue
        relative = Path(entry["provider"]) / entry["folder"] / "SKILL.md"
        backup = profile_dir / "backups" / relative
        changes.append(
            {
                "provider": entry["provider"],
                "folder": entry["folder"],
                "path": str(skill_path),
                "backup": str(backup),
                "disabled": should_disable,
            }
        )
        if args.apply:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_path, backup)
            skill_path.write_text(updated, encoding="utf-8")

    manifest = {
        "id": profile_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "providers": providers,
        "keep_enabled": sorted(keep),
        "changes": changes,
        "applied": bool(args.apply),
    }
    if args.apply:
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(manifest, ensure_ascii=True, indent=2))


def command_restore(args: argparse.Namespace) -> None:
    profile_dir = args.home / "profiles" / args.profile
    manifest_path = profile_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"profile not found: {args.profile}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changes = manifest.get("changes", [])
    restored: list[dict[str, str]] = []

    for change in changes:
        backup = Path(change["backup"])
        target = Path(change["path"])
        if not backup.is_file():
            raise SystemExit(f"backup missing: {backup}")
        if args.apply:
            target.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        restored.append({"path": str(target), "backup": str(backup)})

    result = {
        "profile": args.profile,
        "applied": bool(args.apply),
        "restored": restored,
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))


def list_profiles(args: argparse.Namespace) -> None:
    directory = args.home / "profiles"
    values: list[dict[str, Any]] = []
    if directory.is_dir():
        for manifest in sorted(directory.glob("*/manifest.json")):
            value = json.loads(manifest.read_text(encoding="utf-8"))
            values.append(
                {
                    "id": value.get("id"),
                    "created_at": value.get("created_at"),
                    "providers": value.get("providers"),
                    "keep_enabled": value.get("keep_enabled"),
                    "changes": len(value.get("changes", [])),
                    "applied": value.get("applied"),
                }
            )
    print(json.dumps(values, ensure_ascii=True, indent=2))


def main() -> None:
    args = build_parser().parse_args()
    commands = {
        "report": command_report,
        "apply": command_apply,
        "restore": command_restore,
        "list-profiles": list_profiles,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
