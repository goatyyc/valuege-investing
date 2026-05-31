#!/usr/bin/env python3
"""Install a daily macOS launchd job for ValueGe dataset updates."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys


REPO_DIR = Path(__file__).resolve().parents[1]
LABEL = "com.valuege-investing.update"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_DIR = REPO_DIR / "logs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hour", type=int, default=8)
    parser.add_argument("--minute", type=int, default=30)
    parser.add_argument("--no-load", action="store_true", help="Write the plist but do not load it.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [
            sys.executable,
            str(REPO_DIR / "scripts" / "update_and_commit.py"),
        ],
        "WorkingDirectory": str(REPO_DIR),
        "StartCalendarInterval": {"Hour": args.hour, "Minute": args.minute},
        "StandardOutPath": str(LOG_DIR / "launchd-update.log"),
        "StandardErrorPath": str(LOG_DIR / "launchd-update.err.log"),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "VALUEGE_AUTO_PUSH": "1",
        },
    }
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PLIST_PATH.open("wb") as handle:
        plistlib.dump(plist, handle)
    print(f"Wrote {PLIST_PATH}")
    if not args.no_load:
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(PLIST_PATH)], check=False)
        subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH)], check=True)
        subprocess.run(["launchctl", "enable", f"gui/{os.getuid()}/{LABEL}"], check=True)
        print(f"Loaded {LABEL} for daily {args.hour:02d}:{args.minute:02d} local time")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

