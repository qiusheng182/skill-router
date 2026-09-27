#!/usr/bin/env python3
"""Build compact, query-scoped context packs for any installed skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from provider_roots import provider_roots


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "use",
    "using",
    "with",
}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def parse_frontmatter_end(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return -1
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index
    return -1


def query_terms(query: str) -> list[str]:
    return [
        term
        for term in re.findall(r"[a-zA-Z0-9_-]+", query.lower())
        if len(term) > 2 and term not in STOPWORDS
    ]


def score_text(text: str, terms: list[str]) -> int:
    if not terms:
        return 0
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def is_core_heading(heading: str) -> bool:
    lowered = heading.lower()
    return any(
        marker in lowered
        for marker in (
            "overview",
            "safety",
            "boundary",
            "requirement",
            "quick",
            "workflow",
            "output",
            "rules",
            "priority",
            "clarification",
            "constraint",
        )
    )


def parse_skill_sections(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines(keepends=True)
    frontmatter_end = parse_frontmatter_end(lines)
    sections: list[dict[str, Any]] = []

    if frontmatter_end >= 0:
        block = "".join(lines[: frontmatter_end + 1])
        sections.append(
            {
                "heading": "Frontmatter",
                "start_line": 1,
                "end_line": frontmatter_end + 1,
                "text": block,
                "tokens": estimate_tokens(block),
            }
        )
        body_start = frontmatter_end + 1
    else:
        body_start = 0

    heading_indexes = []
    fence_marker = ""
    for index in range(body_start, len(lines)):
        fence = re.match(r"^\s*(```+|~~~+)", lines[index])
        if fence:
            marker = fence.group(1)[0]
            if not fence_marker:
                fence_marker = marker
            elif fence_marker == marker:
                fence_marker = ""
            continue
        if not fence_marker and re.match(r"^##\s+", lines[index]):
            heading_indexes.append(index)
    if not heading_indexes:
        block = "".join(lines[body_start:])
        if block.strip():
            sections.append(
                {
                    "heading": "Body",
                    "start_line": body_start + 1,
                    "end_line": len(lines),
                    "text": block,
                    "tokens": estimate_tokens(block),
                }
            )
        return sections

    for position, start in enumerate(heading_indexes):
        end = (
            heading_indexes[position + 1] - 1
            if position + 1 < len(heading_indexes)
            else len(lines) - 1
        )
        block = "".join(lines[start : end + 1])
        sections.append(
            {
                "heading": lines[start].strip(),
                "start_line": start + 1,
                "end_line": end + 1,
                "text": block,
                "tokens": estimate_tokens(block),
            }
        )
    return sections


def reference_entries(skill_path: Path, terms: list[str]) -> list[dict[str, Any]]:
    reference_root = skill_path / "references"
    if not reference_root.is_dir():
        return []
    entries = []
    for path in sorted(reference_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = read_text(path)
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(skill_path).as_posix()
        entries.append(
            {
                "path": relative,
                "tokens": estimate_tokens(text),
                "score": score_text(relative + "\n" + text[:4000], terms),
            }
        )
    return sorted(entries, key=lambda item: (-item["score"], item["path"]))


def select_sections(
    sections: list[dict[str, Any]],
    terms: list[str],
    budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scored = []
    for position, section in enumerate(sections):
        score = score_text(section["text"], terms)
        if section["heading"] == "Frontmatter":
            score += 1000
        elif is_core_heading(section["heading"]):
            score += 20
        scored.append((score, position, section))

    selected: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    used = 0
    for score, _, section in sorted(
        scored,
        key=lambda item: (-item[0], item[1]),
    ):
        if score <= 0:
            omitted.append(section)
            continue
        if used + section["tokens"] <= budget or not selected:
            selected.append(section)
            used += section["tokens"]
        else:
            omitted.append(section)
    return selected, omitted


def render_pack(
    skill_path: Path,
    query: str,
    budget: int,
    include_references: set[str],
) -> str:
    skill_file = skill_path / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"missing SKILL.md: {skill_path}")

    text = read_text(skill_file)
    terms = query_terms(query)
    sections = parse_skill_sections(text)
    selected, omitted = select_sections(sections, terms, budget)
    references = reference_entries(skill_path, terms)

    output = [
        f"# Context Pack: {skill_path.name}",
        "",
        f"Source: {skill_file}",
        f"Query: {query or '<none>'}",
        f"Budget: {budget} estimated tokens",
        "",
        "## Included",
        "",
    ]

    for section in selected:
        output.append(
            f"### {section['heading']} "
            f"(lines {section['start_line']}-{section['end_line']})"
        )
        output.append("")
        output.append(section["text"].rstrip())
        output.append("")

    if omitted:
        output.extend(
            [
                "## Omitted Sections",
                "",
                "Load these only if the task needs that topic:",
                "",
            ]
        )
        for section in omitted:
            output.append(
                f"- {section['heading']} "
                f"(lines {section['start_line']}-{section['end_line']}, "
                f"~{section['tokens']} tokens)"
            )
        output.append("")

    if references:
        output.extend(
            [
                "## Available References",
                "",
                "Load a reference only when its topic matches the task:",
                "",
            ]
        )
        for entry in references:
            marker = " [included]" if entry["path"] in include_references else ""
            output.append(
                f"- {entry['path']} "
                f"(~{entry['tokens']} tokens, score={entry['score']}){marker}"
            )
        output.append("")

        for entry in references:
            if entry["path"] not in include_references:
                continue
            output.append(f"### Reference: {entry['path']}")
            output.append("")
            output.append(read_text(skill_path / entry["path"]).rstrip())
            output.append("")

    return "\n".join(output).rstrip() + "\n"


def command_pack(args: argparse.Namespace) -> None:
    output = render_pack(
        args.skill_path.resolve(),
        args.query,
        args.budget,
        set(args.include_reference or []),
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)


def command_manifest(args: argparse.Namespace) -> None:
    skill_path = args.skill_path.resolve()
    text = read_text(skill_path / "SKILL.md")
    manifest = {
        "skill": skill_path.name,
        "path": str(skill_path),
        "estimated_tokens": estimate_tokens(text),
        "sections": [
            {
                "heading": section["heading"],
                "start_line": section["start_line"],
                "end_line": section["end_line"],
                "tokens": section["tokens"],
            }
            for section in parse_skill_sections(text)
        ],
        "references": reference_entries(skill_path, []),
    }
    print(json.dumps(manifest, ensure_ascii=True, indent=2))


def command_audit(args: argparse.Namespace) -> None:
    roots = provider_roots()
    providers = [
        value.strip().lower()
        for value in args.provider.split(",")
        if value.strip()
    ]
    for value in args.root or []:
        name, separator, path = value.partition("=")
        if not separator or not name.strip() or not path.strip():
            raise SystemExit(f"invalid --root value: {value}")
        roots[name.strip().lower()] = Path(path.strip())
        if name.strip().lower() not in providers:
            providers.append(name.strip().lower())

    skill_files: list[Path] = []
    for provider in providers:
        root = roots.get(provider)
        if root is None or not root.is_dir():
            continue
        if args.recursive:
            skill_files.extend(root.rglob("SKILL.md"))
        else:
            skill_files.extend(
                child / "SKILL.md"
                for child in sorted(root.iterdir())
                if child.is_dir() and (child / "SKILL.md").is_file()
            )

    report = []
    for skill_file in sorted(set(skill_files)):
        skill_path = skill_file.parent
        try:
            text = read_text(skill_file)
        except UnicodeDecodeError:
            continue
        references = reference_entries(skill_path, [])
        skill_tokens = estimate_tokens(text)
        reference_tokens = sum(item["tokens"] for item in references)
        if skill_tokens < args.min_tokens and reference_tokens < args.min_tokens:
            continue
        report.append(
            {
                "skill": skill_path.name,
                "path": str(skill_path),
                "skill_md_tokens": skill_tokens,
                "reference_tokens": reference_tokens,
                "reference_files": len(references),
                "potential_savings": max(0, skill_tokens - args.budget)
                + reference_tokens,
            }
        )

    report.sort(key=lambda item: (-item["potential_savings"], item["skill"]))
    if args.top > 0:
        report = report[: args.top]
    print(
        json.dumps(
            {
                "budget": args.budget,
                "min_tokens": args.min_tokens,
                "providers": providers,
                "skills": report,
            },
            ensure_ascii=True,
            indent=2,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    pack = subparsers.add_parser("pack")
    pack.add_argument("--skill-path", type=Path, required=True)
    pack.add_argument("--query", default="")
    pack.add_argument("--budget", type=int, default=1500)
    pack.add_argument("--include-reference", action="append")
    pack.add_argument("--output", type=Path)
    pack.set_defaults(func=command_pack)

    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("--skill-path", type=Path, required=True)
    manifest.set_defaults(func=command_manifest)

    audit = subparsers.add_parser("audit")
    audit.add_argument("--provider", default="codex")
    audit.add_argument("--root", action="append")
    audit.add_argument("--recursive", action="store_true")
    audit.add_argument("--budget", type=int, default=1500)
    audit.add_argument("--min-tokens", type=int, default=1000)
    audit.add_argument("--top", type=int, default=20)
    audit.set_defaults(func=command_audit)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
