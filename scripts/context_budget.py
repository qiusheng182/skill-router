#!/usr/bin/env python3
"""Reduce per-request skill context by making non-router skills user-invoked."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from provider_roots import provider_roots


DISABLE_KEY = "disable-model-invocation"


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def read_frontmatter(text: str) -> tuple[list[str], int, int]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return [], -1, -1
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines, 0, index
    return [], -1, -1


def frontmatter_value(lines: list[str], key: str) -> str:
    pattern = rf"^\s*{re.escape(key)}\s*:\s*(.*?)\s*$"
    for line in lines[1:]:
        match = re.match(pattern, line.rstrip("\r\n"))
        if match:
            return match.group(1).strip().strip("\"'")
    return ""


def set_disable_flag(text: str, disable: bool) -> tuple[str, bool]:
    lines, start, end = read_frontmatter(text)
    if start < 0 or end < 0:
        raise ValueError("SKILL.md is missing valid frontmatter")

    existing = None
    for index in range(1, end):
        if re.match(rf"^\s*{re.escape(DISABLE_KEY)}\s*:", lines[index]):
            existing = index
            break

    if disable and existing is not None:
        if re.match(
            rf"^\s*{re.escape(DISABLE_KEY)}\s*:\s*true\s*$",
            lines[existing].strip(),
            re.IGNORECASE,
        ):
            return text, False
        newline = "\r\n" if lines[existing].endswith("\r\n") else "\n"
        lines[existing] = f"{DISABLE_KEY}: true{newline}"
        return "".join(lines), True

    if not disable and existing is not None:
        del lines[existing]
        return "".join(lines), True

    if disable:
        newline = "\r\n" if lines[end].endswith("\r\n") else "\n"
        lines.insert(end, f"{DISABLE_KEY}: true{newline}")
        return "".join(lines), True

    return text, False


def backup_skill_file(
    skill_file: Path,
    backup_root: Path,
    provider: str,
    skill_name: str,
) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    target = backup_root / provider / skill_name / f"{stamp}-SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill_file, target)
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        default="codex",
        help="comma-separated providers; default: codex",
    )
    parser.add_argument(
        "--keep",
        default="skill-router",
        help="comma-separated skill names that remain model-invoked",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path.home() / ".codex" / "skill-evolution" / "context-backups",
    )
    parser.add_argument(
        "--root",
        action="append",
        help="extra root as name=path",
    )
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roots = provider_roots()
    providers = [
        value.strip().lower()
        for value in args.provider.split(",")
        if value.strip()
    ]
    builtin_providers = set(providers)
    keep = {
        value.strip()
        for value in args.keep.split(",")
        if value.strip()
    }

    unknown = sorted(set(providers) - set(roots))
    if unknown:
        raise SystemExit(f"unknown providers: {', '.join(unknown)}")

    for value in args.root or []:
        name, separator, path = value.partition("=")
        if not separator or not name.strip() or not path.strip():
            raise SystemExit(f"invalid --root value: {value}")
        custom_name = name.strip().lower()
        roots[custom_name] = Path(path.strip())
        if custom_name not in providers:
            providers.append(custom_name)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "apply": args.apply,
        "providers": providers,
        "keep": sorted(keep),
        "skills": [],
        "estimated_context_tokens_saved": 0,
    }

    for provider in providers:
        root = roots[provider]
        if not root.is_dir():
            continue

        if args.recursive and provider not in builtin_providers:
            skill_files = sorted(root.rglob("SKILL.md"))
        else:
            skill_files = [
                child / "SKILL.md"
                for child in sorted(root.iterdir())
                if child.is_dir() and (child / "SKILL.md").is_file()
            ]

        for skill_file in skill_files:
            skill_dir = skill_file.parent

            text = skill_file.read_text(encoding="utf-8-sig")
            lines, start, end = read_frontmatter(text)
            name = frontmatter_value(lines, "name") or skill_dir.name
            description = frontmatter_value(lines, "description")
            should_disable = name not in keep
            try:
                updated, changed = set_disable_flag(text, should_disable)
            except ValueError as error:
                report["skills"].append(
                    {
                        "provider": provider,
                        "name": name,
                        "action": "error",
                        "error": str(error),
                    }
                )
                continue

            if not should_disable:
                action = "keep"
                savings = 0
            elif changed:
                action = "disable"
                savings = estimate_tokens(description)
            else:
                action = "already-disabled"
                savings = 0

            saved_to = ""
            if args.apply and changed:
                saved_to = str(
                    backup_skill_file(
                        skill_file,
                        args.backup_dir,
                        provider,
                        skill_dir.name,
                    )
                )
                skill_file.write_text(updated, encoding="utf-8", newline="")

            report["estimated_context_tokens_saved"] += savings
            report["skills"].append(
                {
                    "provider": provider,
                    "name": name,
                    "action": action,
                    "estimated_tokens_saved": savings,
                    "backup": saved_to,
                }
            )

    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
