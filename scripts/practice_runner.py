#!/usr/bin/env python3
"""Run repeatable practice suites and compare skill versions."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
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


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def validate_suite(suite: dict[str, Any]) -> list[dict[str, Any]]:
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("suite must contain a non-empty cases array")
    for index, case in enumerate(cases, 1):
        if not isinstance(case, dict):
            raise ValueError(f"case {index} must be an object")
        if not case.get("id"):
            raise ValueError(f"case {index} is missing id")
        command = case.get("command")
        if not isinstance(command, list) or not all(
            isinstance(part, str) for part in command
        ):
            raise ValueError(f"case {index} command must be a string array")
        for key in (
            "expect_stdout_contains",
            "expect_stdout_not_contains",
            "expect_stderr_contains",
        ):
            value = case.get(key, [])
            if not isinstance(value, list) or not all(
                isinstance(part, str) for part in value
            ):
                raise ValueError(f"case {index} {key} must be a string array")
    return cases


def evaluate_case(
    case: dict[str, Any],
    *,
    suite_dir: Path,
    default_cwd: Path,
    default_timeout: float,
) -> dict[str, Any]:
    command = case["command"]
    raw_cwd = case.get("cwd")
    cwd = (
        (suite_dir / raw_cwd).resolve()
        if raw_cwd
        else default_cwd.resolve()
    )
    timeout = float(case.get("timeout", default_timeout))
    expected_exit = int(case.get("expect_exit", 0))
    start = time.perf_counter()
    failures: list[str] = []

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code: int | None = completed.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        exit_code = None
        failures.append(f"timed out after {timeout}s")

    duration = time.perf_counter() - start
    if exit_code != expected_exit:
        failures.append(f"exit code {exit_code} != {expected_exit}")
    for expected in case.get("expect_stdout_contains", []):
        if expected not in stdout:
            failures.append(f"stdout missing {expected!r}")
    for expected in case.get("expect_stderr_contains", []):
        if expected not in stderr:
            failures.append(f"stderr missing {expected!r}")
    for unexpected in case.get("expect_stdout_not_contains", []):
        if unexpected in stdout:
            failures.append(f"stdout unexpectedly contains {unexpected!r}")

    return {
        "id": case["id"],
        "name": case.get("name") or case["id"],
        "passed": not failures,
        "exit_code": exit_code,
        "expected_exit": expected_exit,
        "duration_s": round(duration, 4),
        "output_tokens": estimate_tokens(stdout + stderr),
        "failures": failures,
        "stdout_tail": stdout[-1200:],
        "stderr_tail": stderr[-1200:],
    }


def command_run(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    suite_path = args.suite.resolve()
    suite = load_json(suite_path)
    cases = validate_suite(suite)
    skill = args.skill or str(suite.get("skill") or "")
    if not skill:
        raise ValueError("skill is required")

    report_id = make_id("PR")
    started_at = utc_now()
    results = [
        evaluate_case(
            case,
            suite_dir=suite_path.parent,
            default_cwd=args.cwd,
            default_timeout=args.timeout,
        )
        for case in cases
    ]
    passed = sum(1 for result in results if result["passed"])
    report = {
        "id": report_id,
        "skill": skill,
        "name": args.name or suite_path.stem,
        "suite": str(suite_path),
        "started_at": started_at,
        "finished_at": utc_now(),
        "total_cases": len(results),
        "passed_cases": passed,
        "failed_cases": len(results) - passed,
        "pass_rate": round(passed / len(results), 4),
        "total_duration_s": round(
            sum(result["duration_s"] for result in results), 4
        ),
        "output_tokens": sum(result["output_tokens"] for result in results),
        "cases": results,
    }
    report_path = args.home / "practice-reports" / f"{report_id}.json"
    write_json(report_path, report)

    if args.verbose:
        output = report
    else:
        output = {
            key: report[key]
            for key in (
                "id",
                "skill",
                "name",
                "total_cases",
                "passed_cases",
                "failed_cases",
                "pass_rate",
                "total_duration_s",
                "output_tokens",
            )
        }
        output["failed"] = [
            {
                "id": result["id"],
                "failures": result["failures"],
            }
            for result in results
            if not result["passed"]
        ]
    output["report"] = str(report_path)
    print(json.dumps(output, ensure_ascii=True, indent=2))


def command_compare(args: argparse.Namespace) -> None:
    old = load_json(args.old.resolve())
    new = load_json(args.new.resolve())
    if old.get("skill") != new.get("skill"):
        raise ValueError("reports must belong to the same skill")

    old_cases = {case["id"]: case for case in old.get("cases", [])}
    new_cases = {case["id"]: case for case in new.get("cases", [])}
    improved = sorted(
        case_id
        for case_id in old_cases.keys() & new_cases.keys()
        if not old_cases[case_id]["passed"] and new_cases[case_id]["passed"]
    )
    regressed = sorted(
        case_id
        for case_id in old_cases.keys() & new_cases.keys()
        if old_cases[case_id]["passed"] and not new_cases[case_id]["passed"]
    )
    added = sorted(new_cases.keys() - old_cases.keys())
    removed = sorted(old_cases.keys() - new_cases.keys())

    delta_pass_rate = round(
        float(new.get("pass_rate", 0)) - float(old.get("pass_rate", 0)),
        4,
    )
    delta_duration = round(
        float(new.get("total_duration_s", 0))
        - float(old.get("total_duration_s", 0)),
        4,
    )
    delta_tokens = int(new.get("output_tokens", 0)) - int(
        old.get("output_tokens", 0)
    )
    if regressed:
        verdict = "regressed"
    elif improved or delta_pass_rate > 0:
        verdict = "improved"
    else:
        verdict = "neutral"

    print(
        json.dumps(
            {
                "skill": new.get("skill"),
                "old_report": str(args.old),
                "new_report": str(args.new),
                "verdict": verdict,
                "delta_pass_rate": delta_pass_rate,
                "delta_duration_s": delta_duration,
                "delta_output_tokens": delta_tokens,
                "improved_cases": improved,
                "regressed_cases": regressed,
                "added_cases": added,
                "removed_cases": removed,
            },
            ensure_ascii=True,
            indent=2,
        )
    )


def command_list(args: argparse.Namespace) -> None:
    ensure_home(args.home)
    reports = []
    for path in sorted((args.home / "practice-reports").glob("*.json")):
        report = load_json(path)
        if args.skill and report.get("skill") != args.skill:
            continue
        reports.append(
            {
                "id": report.get("id"),
                "skill": report.get("skill"),
                "name": report.get("name"),
                "finished_at": report.get("finished_at"),
                "pass_rate": report.get("pass_rate"),
                "output_tokens": report.get("output_tokens"),
                "path": str(path),
            }
        )
    reports.sort(key=lambda item: item.get("finished_at", ""), reverse=True)
    print(json.dumps(reports[: args.top], ensure_ascii=True, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=default_home())
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--suite", type=Path, required=True)
    run.add_argument("--skill")
    run.add_argument("--name")
    run.add_argument("--cwd", type=Path, default=Path.cwd())
    run.add_argument("--timeout", type=float, default=300.0)
    run.add_argument("--verbose", action="store_true")
    run.set_defaults(func=command_run)

    compare = subparsers.add_parser("compare")
    compare.add_argument("--old", type=Path, required=True)
    compare.add_argument("--new", type=Path, required=True)
    compare.set_defaults(func=command_compare)

    listing = subparsers.add_parser("list")
    listing.add_argument("--skill")
    listing.add_argument("--top", type=int, default=20)
    listing.set_defaults(func=command_list)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: {error}")


if __name__ == "__main__":
    main()
