#!/usr/bin/env python3
"""Record and query per-skill practice episodes."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from learning_store import (
    default_home,
    ensure_home,
    load_json,
    make_id,
    utc_now,
    write_json,
)


OUTCOMES = {"success", "partial", "failure"}


def parse_metric(values: list[str] | None) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for value in values or []:
        key, separator, raw = value.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"invalid metric: {value}")
        key = key.strip()
        raw = raw.strip()
        try:
            parsed: Any = int(raw)
        except ValueError:
            try:
                parsed = float(raw)
            except ValueError:
                parsed = raw
        metrics[key] = parsed
    return metrics


def load_episodes(home: Path) -> list[dict[str, Any]]:
    directory = home / "experiences"
    return [load_json(path) for path in sorted(directory.glob("*.json"))]


def brief_episode(episode: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": episode.get("id"),
        "created_at": episode.get("created_at"),
        "skill": episode.get("skill"),
        "outcome": episode.get("outcome"),
        "task": episode.get("task"),
        "tags": episode.get("tags", []),
        "metrics": episode.get("metrics", {}),
    }


def command_record(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    if not args.skill.strip():
        raise ValueError("skill is required")
    if not args.task.strip():
        raise ValueError("task is required")
    if not args.summary.strip():
        raise ValueError("summary is required")

    episode_id = make_id("EX")
    episode = {
        "id": episode_id,
        "created_at": utc_now(),
        "skill": args.skill.strip(),
        "task": args.task,
        "outcome": args.outcome,
        "summary": args.summary,
        "failures": list(args.failure or []),
        "resolution": args.resolution or "",
        "corrections": list(args.correction or []),
        "tags": list(args.tag or []),
        "tools": list(args.tool or []),
        "environment": args.environment or "",
        "metrics": parse_metric(args.metric),
        "evidence": list(args.evidence or []),
        "sources": list(args.source or []),
        "generalizability": args.generalizability,
    }
    path = args.home / "experiences" / f"{episode_id}.json"
    write_json(path, episode)
    print(json.dumps({"id": episode_id, "path": str(path)}, ensure_ascii=True))


def command_list(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    episodes = load_episodes(args.home)
    if args.skill:
        episodes = [
            episode
            for episode in episodes
            if episode.get("skill") == args.skill
        ]
    if args.outcome:
        episodes = [
            episode
            for episode in episodes
            if episode.get("outcome") == args.outcome
        ]
    if args.tag:
        episodes = [
            episode
            for episode in episodes
            if args.tag in episode.get("tags", [])
        ]
    episodes.sort(key=lambda episode: episode.get("created_at", ""), reverse=True)

    output = (
        [brief_episode(episode) for episode in episodes]
        if args.brief
        else episodes
    )
    print(json.dumps(output, ensure_ascii=True, indent=2))


def command_show(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    path = args.home / "experiences" / f"{args.id}.json"
    if not path.is_file():
        raise ValueError(f"experience not found: {args.id}")
    print(json.dumps(load_json(path), ensure_ascii=True, indent=2))


def command_scorecard(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    episodes = [
        episode
        for episode in load_episodes(args.home)
        if episode.get("skill") == args.skill
    ]
    episodes.sort(key=lambda episode: episode.get("created_at", ""))

    outcome_counts = Counter(episode.get("outcome", "unknown") for episode in episodes)
    failure_counts = Counter(
        failure
        for episode in episodes
        for failure in episode.get("failures", [])
    )
    tag_counts = Counter(
        tag for episode in episodes for tag in episode.get("tags", [])
    )
    token_values = [
        int(episode["metrics"]["tokens"])
        for episode in episodes
        if isinstance(episode.get("metrics"), dict)
        and isinstance(episode["metrics"].get("tokens"), (int, float))
    ]
    duration_values = [
        float(episode["metrics"]["duration_s"])
        for episode in episodes
        if isinstance(episode.get("metrics"), dict)
        and isinstance(episode["metrics"].get("duration_s"), (int, float))
    ]
    total = len(episodes)
    success = outcome_counts.get("success", 0)
    partial = outcome_counts.get("partial", 0)

    scorecard = {
        "skill": args.skill,
        "episodes": total,
        "outcomes": dict(outcome_counts),
        "success_rate": round((success + partial * 0.5) / total, 4)
        if total
        else 0,
        "average_tokens": round(sum(token_values) / len(token_values), 2)
        if token_values
        else None,
        "average_duration_s": round(
            sum(duration_values) / len(duration_values), 3
        )
        if duration_values
        else None,
        "top_failures": failure_counts.most_common(args.top),
        "top_tags": tag_counts.most_common(args.top),
        "last_episode_at": episodes[-1].get("created_at") if episodes else None,
        "recent_episodes": [
            brief_episode(episode) for episode in episodes[-args.recent :]
        ],
    }
    print(json.dumps(scorecard, ensure_ascii=True, indent=2))


def command_relevant(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    terms = [
        term
        for term in re.findall(r"[a-zA-Z0-9_-]+", args.query.lower())
        if len(term) > 2
    ]
    scored = []
    for episode in load_episodes(args.home):
        if episode.get("skill") != args.skill:
            continue
        haystack = " ".join(
            [
                str(episode.get("task", "")),
                str(episode.get("summary", "")),
                str(episode.get("resolution", "")),
                " ".join(episode.get("failures", [])),
                " ".join(episode.get("tags", [])),
            ]
        ).lower()
        score = sum(haystack.count(term) for term in terms)
        if score or not terms:
            scored.append((score, episode.get("created_at", ""), episode))

    scored.sort(key=lambda item: (-item[0], item[1]), reverse=False)
    selected = [item[2] for item in scored[: args.limit]]
    print(
        json.dumps(
            [brief_episode(episode) for episode in selected],
            ensure_ascii=True,
            indent=2,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=default_home())
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record")
    record.add_argument("--skill", required=True)
    record.add_argument("--task", required=True)
    record.add_argument("--outcome", choices=sorted(OUTCOMES), required=True)
    record.add_argument("--summary", required=True)
    record.add_argument("--failure", action="append")
    record.add_argument("--resolution")
    record.add_argument("--correction", action="append")
    record.add_argument("--tag", action="append")
    record.add_argument("--tool", action="append")
    record.add_argument("--environment")
    record.add_argument("--metric", action="append")
    record.add_argument("--evidence", action="append")
    record.add_argument("--source", action="append")
    record.add_argument(
        "--generalizability",
        choices=("one_off", "pattern", "principle"),
        default="one_off",
    )
    record.set_defaults(func=command_record)

    listing = subparsers.add_parser("list")
    listing.add_argument("--skill")
    listing.add_argument("--outcome", choices=sorted(OUTCOMES))
    listing.add_argument("--tag")
    listing.add_argument("--brief", action="store_true")
    listing.set_defaults(func=command_list)

    show = subparsers.add_parser("show")
    show.add_argument("--id", required=True)
    show.set_defaults(func=command_show)

    scorecard = subparsers.add_parser("scorecard")
    scorecard.add_argument("--skill", required=True)
    scorecard.add_argument("--top", type=int, default=5)
    scorecard.add_argument("--recent", type=int, default=5)
    scorecard.set_defaults(func=command_scorecard)

    relevant = subparsers.add_parser("relevant")
    relevant.add_argument("--skill", required=True)
    relevant.add_argument("--query", required=True)
    relevant.add_argument("--limit", type=int, default=5)
    relevant.set_defaults(func=command_relevant)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: {error}")


if __name__ == "__main__":
    main()
