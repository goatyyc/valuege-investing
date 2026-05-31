#!/usr/bin/env python3
"""Incrementally update the dataset, commit generated changes, and optionally push."""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import subprocess
import sys


REPO_DIR = Path(__file__).resolve().parents[1]
GENERATED_PATHS = [
    "references/data/activities.jsonl",
    "references/data/topics.jsonl",
    "references/data/operations.jsonl",
    "references/data/profile.json",
    "references/data/symbol_index.json",
    "references/data/symbol_dossiers.json",
    "references/data/theme_index.json",
    "references/data/dataset-summary.md",
    "references/symbol-research-view.md",
    "references/theme-research-view.md",
]


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=REPO_DIR, text=True, check=check)


def output(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=REPO_DIR, text=True).strip()


def ensure_clean_worktree() -> None:
    status = output(["git", "status", "--porcelain"])
    if status:
        print("Working tree is not clean; refusing to mix scheduled updates with local edits.", file=sys.stderr)
        print(status, file=sys.stderr)
        raise SystemExit(2)


def has_generated_diff() -> bool:
    result = subprocess.run(
        ["git", "diff", "--quiet", "--"] + GENERATED_PATHS,
        cwd=REPO_DIR,
        check=False,
    )
    return result.returncode == 1


def remote_exists() -> bool:
    result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=REPO_DIR, check=False, stdout=subprocess.DEVNULL)
    return result.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-push", action="store_true", help="Commit locally but do not push to origin.")
    parser.add_argument("--max-pages", type=int, default=3, help="Maximum recent activity pages to scan.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--sleep", type=float, default=0.12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_clean_worktree()
    fetch_cmd = [
        sys.executable,
        "scripts/fetch_longbridge.py",
        "--incremental",
        "--resume-existing-topics",
        "--workers",
        str(args.workers),
        "--sleep",
        str(args.sleep),
        "--max-pages",
        str(args.max_pages),
    ]
    run(fetch_cmd)
    run([sys.executable, "scripts/build_research_views.py"])
    if not has_generated_diff():
        print("No generated data changes to commit.")
        return 0
    run(["git", "add", "--"] + GENERATED_PATHS)
    today = dt.datetime.now().strftime("%Y-%m-%d")
    run(["git", "commit", "-m", f"Update ValueGe Longbridge data {today}"])
    auto_push = os.environ.get("VALUEGE_AUTO_PUSH", "1") != "0"
    if auto_push and not args.no_push and remote_exists():
        run(["git", "push"])
    else:
        print("Skipping push; either disabled or no origin remote is configured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

