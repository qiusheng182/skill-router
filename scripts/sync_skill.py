#!/usr/bin/env python3
"""Synchronize one canonical skill to provider roots."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from provider_roots import parse_custom_roots, provider_roots


def file_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def compare(source: Path, destination: Path) -> dict[str, list[str]]:
    source_hashes = file_hashes(source)
    destination_hashes = (
        file_hashes(destination) if destination.is_dir() else {}
    )
    missing_or_changed = [
        path
        for path, digest in source_hashes.items()
        if destination_hashes.get(path) != digest
    ]
    extra = sorted(set(destination_hashes) - set(source_hashes))
    return {
        "missing_or_changed": missing_or_changed,
        "extra": extra,
    }


def ensure_destination_is_safe(destination: Path, root: Path) -> None:
    resolved_destination = destination.resolve()
    resolved_root = root.resolve()
    if resolved_destination == resolved_root:
        raise ValueError("destination cannot equal the provider root")
    if resolved_root not in resolved_destination.parents:
        raise ValueError(f"destination is outside provider root: {destination}")


def copy_skill(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def backup_skill(
    destination: Path,
    backup_root: Path,
    provider: str,
    skill_name: str,
) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    target = backup_root / skill_name / f"{provider}-{stamp}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(destination, target)
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--providers", default="codex,opencode")
    parser.add_argument("--root", action="append")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--prune", action="store_true")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path.home() / ".codex" / "skill-evolution" / "sync-backups",
    )
    parser.add_argument("--no-backup", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roots = provider_roots()
    roots.update(parse_custom_roots(args.root))

    source = (
        args.source.resolve()
        if args.source
        else (roots["codex"] / args.skill_name).resolve()
    )
    if not (source / "SKILL.md").is_file():
        raise SystemExit(f"source skill is missing SKILL.md: {source}")

    requested = [
        value.strip().lower()
        for value in args.providers.split(",")
        if value.strip()
    ]
    unknown = sorted(set(requested) - set(roots))
    if unknown:
        raise SystemExit(f"unknown providers: {', '.join(unknown)}")

    for provider in requested:
        destination = (roots[provider] / args.skill_name).resolve()
        ensure_destination_is_safe(destination, roots[provider])
        if destination == source:
            print(f"{provider}: source is canonical ({destination})")
            continue

        differences = compare(source, destination)
        if args.check:
            status = (
                "ok"
                if not differences["missing_or_changed"]
                and not differences["extra"]
                else "different"
            )
            print(
                f"{provider}: {status} ({destination}) "
                f"changed={len(differences['missing_or_changed'])} "
                f"extra={len(differences['extra'])}"
            )
            continue

        if destination.is_dir() and differences["missing_or_changed"] and not args.no_backup:
            backup = backup_skill(
                destination,
                args.backup_dir,
                provider,
                args.skill_name,
            )
            print(f"{provider}: backed up to {backup}")

        copy_skill(source, destination)
        if args.prune:
            for relative in differences["extra"]:
                (destination / relative).unlink()
        print(f"{provider}: synced ({destination})")


if __name__ == "__main__":
    main()
