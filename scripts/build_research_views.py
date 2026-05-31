#!/usr/bin/env python3
"""Build compact research views from the local ValueGe dataset."""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import json
from pathlib import Path
import re
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = SKILL_DIR / "references" / "data"

THEMES = {
    "longcall": r"long\s*call|longcall|买.*call|call",
    "put": r"\bput\b|PUT|卖.*put|卖put",
    "core_holdings": r"核心持仓|核心持股|正股|非卖品|不会动|不动.*持仓",
    "cashflow": r"现金流|收现金|自由现金流",
    "time_friend": r"和时间做朋友|长期|长持|慢慢",
    "safety_margin": r"安全边际|王子落难|困境反转",
    "watchlist": r"观察仓|关注|做功课|等机会|给机会|准备",
    "risk_control": r"不懂不碰|拿不准|分批|仓位|控制",
    "small_growth": r"小票|成长|增长潜力|高风险|小仓位",
}

THEME_LABELS = {
    "longcall": "longcall / 买 call",
    "put": "put / 卖 put",
    "core_holdings": "核心持仓 / 正股",
    "cashflow": "现金流",
    "time_friend": "和时间做朋友 / 长期",
    "safety_margin": "安全边际 / 王子落难",
    "watchlist": "观察仓 / 等机会",
    "risk_control": "风控 / 分批 / 不懂不碰",
    "small_growth": "小票成长 / 小仓位",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact(value: str, limit: int = 92) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def date_of(row: dict[str, Any]) -> str:
    return row.get("date") or str(row.get("created_at_local") or "")[:10]


def level_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row.get("evidence_level") or row.get("level") or "U" for row in rows)
    return {level: counts.get(level, 0) for level in ["A", "B", "C", "D", "U"]}


def build_symbol_dossiers(topics: list[dict[str, Any]], top_n: int, per_symbol_limit: int) -> dict[str, Any]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for topic in topics:
        for symbol in topic.get("symbols") or []:
            by_symbol[str(symbol)].append(topic)

    ranked_symbols = sorted(by_symbol, key=lambda item: (-len(by_symbol[item]), item))[:top_n]
    dossiers: dict[str, Any] = {}
    for symbol in ranked_symbols:
        rows = by_symbol[symbol]
        evidence_rows = [
            row
            for row in rows
            if row.get("evidence_level") in {"A", "B", "C"}
        ][:per_symbol_limit]
        dossiers[symbol] = {
            "symbol": symbol,
            "total_mentions": len(rows),
            "level_counts": level_counts(rows),
            "recent_evidence": [
                {
                    "date": date_of(row),
                    "level": row.get("evidence_level"),
                    "topic_id": row.get("topic_id"),
                    "summary": row.get("summary"),
                    "url": row.get("url"),
                }
                for row in evidence_rows
            ],
        }
    return dossiers


def build_theme_index(topics: list[dict[str, Any]], per_theme_limit: int) -> dict[str, Any]:
    theme_index: dict[str, Any] = {}
    for key, pattern in THEMES.items():
        regex = re.compile(pattern, re.IGNORECASE)
        matched = [row for row in topics if regex.search(row.get("text") or "")]
        evidence = [row for row in matched if row.get("evidence_level") in {"A", "B", "C"}]
        theme_index[key] = {
            "label": THEME_LABELS[key],
            "pattern": pattern,
            "match_count": len(matched),
            "evidence_count": len(evidence),
            "level_counts": level_counts(matched),
            "recent_evidence": [
                {
                    "date": date_of(row),
                    "level": row.get("evidence_level"),
                    "symbols": row.get("symbols") or [],
                    "topic_id": row.get("topic_id"),
                    "summary": row.get("summary"),
                    "url": row.get("url"),
                }
                for row in evidence[:per_theme_limit]
            ],
        }
    return theme_index


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_symbol_markdown(path: Path, dossiers: dict[str, Any]) -> None:
    table_rows = []
    for symbol, item in dossiers.items():
        counts = item["level_counts"]
        latest = item["recent_evidence"][0] if item["recent_evidence"] else {}
        table_rows.append(
            [
                symbol,
                str(item["total_mentions"]),
                str(counts["A"]),
                str(counts["B"]),
                str(counts["C"]),
                latest.get("date", ""),
                compact(latest.get("summary", ""), 56),
            ]
        )
    content = [
        "# Symbol Research View",
        "",
        "Use this as a starting point for symbol-specific questions. Counts are machine-assisted triage, not verified trades.",
        "",
        markdown_table(
            ["Symbol", "Mentions", "A", "B", "C", "Latest", "Latest evidence"],
            table_rows,
        ),
        "",
        "Before attributing an operation to a symbol, inspect the full topic when a row contains multiple symbols.",
    ]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def write_theme_markdown(path: Path, theme_index: dict[str, Any]) -> None:
    lines = [
        "# Theme Research View",
        "",
        "Use this for framework questions. The examples are recent public-post evidence; summarize by paraphrase and cite topic URLs.",
        "",
    ]
    for key, item in theme_index.items():
        counts = item["level_counts"]
        lines.extend(
            [
                f"## {item['label']}",
                "",
                f"- Matches: {item['match_count']} topics; evidence rows: {item['evidence_count']}; levels A/B/C/D/U = {counts['A']}/{counts['B']}/{counts['C']}/{counts['D']}/{counts['U']}.",
            ]
        )
        for sample in item["recent_evidence"][:5]:
            symbols = ",".join(sample.get("symbols") or [])
            lines.append(
                f"- {sample['date']} [{sample['level']}] {symbols}: {compact(sample['summary'])} ({sample['url']})"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--top-symbols", type=int, default=30)
    parser.add_argument("--per-symbol-limit", type=int, default=18)
    parser.add_argument("--per-theme-limit", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir)
    topics = load_jsonl(data_dir / "topics.jsonl")
    dossiers = build_symbol_dossiers(topics, args.top_symbols, args.per_symbol_limit)
    themes = build_theme_index(topics, args.per_theme_limit)
    write_json(data_dir / "symbol_dossiers.json", dossiers)
    write_json(data_dir / "theme_index.json", themes)
    references_dir = data_dir.parent
    write_symbol_markdown(references_dir / "symbol-research-view.md", dossiers)
    write_theme_markdown(references_dir / "theme-research-view.md", themes)
    print(f"wrote {len(dossiers)} symbol dossiers and {len(themes)} theme views")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
