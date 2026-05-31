#!/usr/bin/env python3
"""Query the local ValueGe Longbridge dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "references" / "data"

SYMBOL_GROUPS = {
    "BABA": {"BABA", "09988", "9988", "89988"},
    "XPEV": {"XPEV", "09868", "9868"},
    "TCEHY": {"TCEHY", "00700", "700"},
    "3690": {"03690", "3690"},
    "1810": {"01810", "1810"},
    "BRK.B": {"BRK.B", "BRKB", "BRK-B"},
}

SYMBOL_ALIASES = {
    "阿里": "BABA",
    "阿里巴巴": "BABA",
    "小鹏": "XPEV",
    "小鹏汽车": "XPEV",
    "腾讯": "TCEHY",
    "腾讯控股": "TCEHY",
    "美团": "3690",
    "小米": "1810",
    "伯克希尔": "BRK.B",
    "伯克希尔哈撒韦": "BRK.B",
    "BRKB": "BRK.B",
    "BRK-B": "BRK.B",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def expand_symbol(symbol: str | None) -> set[str]:
    if not symbol:
        return set()
    raw = symbol.strip()
    upper = raw.upper()
    canonical = SYMBOL_ALIASES.get(raw) or SYMBOL_ALIASES.get(upper) or upper
    if canonical in SYMBOL_GROUPS:
        return {item.upper() for item in SYMBOL_GROUPS[canonical]}
    for group in SYMBOL_GROUPS.values():
        if upper in {item.upper() for item in group}:
            return {item.upper() for item in group}
    return {upper}


def match_row(row: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.topic_id and str(row.get("topic_id") or "") != str(args.topic_id):
        return False
    date = row.get("date") or str(row.get("created_at_local") or "")[:10]
    if args.since and date and date < args.since:
        return False
    if args.until and date and date > args.until:
        return False
    haystack = " ".join(
        [
            str(row.get("summary") or ""),
            str(row.get("text") or ""),
            " ".join(row.get("symbols") or []),
            " ".join(row.get("tags") or row.get("evidence_tags") or []),
        ]
    )
    if args.symbol:
        symbols = {str(item).upper() for item in row.get("symbols") or []}
        if not symbols.intersection(args.symbols_expanded):
            return False
    if args.level and str(row.get("level") or row.get("evidence_level") or "").upper() != args.level.upper():
        return False
    if args.keyword and not re.search(args.keyword, haystack, re.IGNORECASE):
        return False
    return True


def print_rows(rows: list[dict[str, Any]], include_text: bool, output_format: str) -> None:
    for row in rows:
        if output_format == "jsonl":
            print(json.dumps(row, ensure_ascii=False, sort_keys=True))
            continue
        date = row.get("date") or str(row.get("created_at_local") or "")[:10]
        level = row.get("level") or row.get("evidence_level") or ""
        symbols = ",".join(row.get("symbols") or [])
        summary = row.get("summary") or ""
        print(f"{date}\t{level}\t{symbols}\t{summary}\t{row.get('url')}")
        if include_text and row.get("text"):
            print(row["text"].strip())
            print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--source", choices=["operations", "topics"], default="operations")
    parser.add_argument("--symbol")
    parser.add_argument("--level", choices=["A", "B", "C", "D", "U"])
    parser.add_argument("--keyword")
    parser.add_argument("--topic-id")
    parser.add_argument("--since", help="Start date, YYYY-MM-DD")
    parser.add_argument("--until", help="End date, YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--include-text", action="store_true")
    parser.add_argument("--format", choices=["text", "jsonl"], default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.symbols_expanded = expand_symbol(args.symbol)
    data_dir = Path(args.data_dir)
    filename = "operations.jsonl" if args.source == "operations" else "topics.jsonl"
    rows = [row for row in load_jsonl(data_dir / filename) if match_row(row, args)]
    print_rows(rows[: args.limit], args.include_text, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
