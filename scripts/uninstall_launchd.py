#!/usr/bin/env python3
"""Remove the macOS launchd job for ValueGe dataset updates."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess


LABEL = "com.valuege-investing.update"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def main() -> int:
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(PLIST_PATH)], check=False)
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
        print(f"Removed {PLIST_PATH}")
    else:
        print(f"No plist found at {PLIST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

