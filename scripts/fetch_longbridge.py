#!/usr/bin/env python3
"""Fetch and index ValueGe public Longbridge posts.

The script uses the same public Longbridge endpoints the web app calls. It
stores normalized JSONL files plus lightweight Markdown indexes for skill use.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import html
from html.parser import HTMLParser
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASE_URL = "https://m.lbkrs.com/api/forward"
WEB_TOPIC_URL = "https://longbridge.com/zh-CN/topics/{topic_id}"
DEFAULT_MEMBER_ID = "3090"
DEFAULT_SLEEP = 0.12

HEADERS = {
    "accept": "application/json",
    "accept-language": "zh-CN",
    "x-prefer-language": "zh-CN",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "x-platform": "web",
    "x-app-id": "longbridge",
    "x-device-id": "none",
}

ALIASES = {
    "BRKB": "BRK.B",
    "BRK.B": "BRK.B",
    "BRK-A": "BRK.A",
    "BRK.A": "BRK.A",
    "GOOG": "GOOG",
    "GOOGL": "GOOGL",
    "TSLA": "TSLA",
    "AAPL": "AAPL",
    "AMZN": "AMZN",
    "MSFT": "MSFT",
    "NVO": "NVO",
    "RXRX": "RXRX",
    "TSM": "TSM",
    "NVDA": "NVDA",
    "KO": "KO",
    "AMD": "AMD",
    "DXYZ": "DXYZ",
    "SPACEX": "SpaceX",
    "OPENAI": "OpenAI",
    "谷歌": "GOOG",
    "特斯拉": "TSLA",
    "苹果": "AAPL",
    "亚马逊": "AMZN",
    "微软": "MSFT",
    "伯克希尔": "BRK.B",
    "伯克希尔哈撒韦": "BRK.B",
    "台积电": "TSM",
    "英伟达": "NVDA",
    "诺和诺德": "NVO",
    "可口可乐": "KO",
}

OPERATION_PATTERNS = [
    ("buy", r"(买入|买了|买点|再买|继续买|加仓|加了点|补点|补了点|捞了点|捞点|建仓|建了|建个|布局了|布局一点|布局的|搞了点|干一票)"),
    ("sell", r"(卖了|卖出|出了|出点|分批出|清了|清仓|减仓|降成本|降低成本|收现金|整出.*资金)"),
    ("hold", r"(持仓|核心持仓|核心持股|正股|长持|拿着|非卖品|不会动|不动.*持仓|和时间做朋友|躺平)"),
    ("option", r"(longcall|long call|Call|call|PUT|Put|put|期权|卖.*put|买.*call)"),
    ("watch", r"(观察仓|关注|做功课|等机会|给机会|准备|想一下|看看|拿不准)"),
]

INTENT_PATTERN = re.compile(r"(看好|长期|未来|等待|机会|准备|希望|思考|不懂不碰|王子落难|安全边际)")
EXTERNAL_PATTERN = re.compile(r"(财报|段永平|木头姐|索罗斯|伯克希尔.*加仓|贝莱德|BlackRock|新闻|据说|宣布|报告|Q[1-4])")
EXTERNAL_ACTOR_PATTERN = re.compile(r"(段永平|段股神|木头姐|索罗斯|贝莱德|BlackRock|伯克希尔.*(加仓|增持|持仓)|巴菲特|阿贝尔)")
SELF_CONTEXT_PATTERN = re.compile(r"(我|我的|手里|昨晚|夜盘|顺手|本周|今天|前几天|我的操作|我家领导账户)")
SELF_OPERATION_PATTERN = re.compile(r"(分批出|补点|补了点|出点|出了一些|出了点|清了|清仓|建个|建了|加了点|捞了点|卖了|买了|布局了一点|继续.*(买|加|补|捞|出|清|布局))")


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "br", "div", "li"} and self.parts and self.parts[-1] != "\n":
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        text = "".join(self.parts)
        text = html.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t\u00a0]+", " ", text)
        return text.strip()


def html_to_text(value: str | None) -> str:
    if not value:
        return ""
    parser = TextExtractor()
    parser.feed(value)
    return parser.text()


def clean_longbridge_markup(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"\[st\][^#\]]+#([^.\]]+)\.([A-Z]+)\[/st\]", r"$\1(\1.\2)", value)
    text = re.sub(r"\[/?[a-zA-Z0-9_:-]+[^\]]*\]", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    return text.strip()


def request_json(url: str, retries: int = 4, sleep: float = DEFAULT_SLEEP) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read().decode("utf-8")
            data = json.loads(payload)
            if isinstance(data, dict):
                return data
            raise RuntimeError(f"Unexpected JSON root for {url}")
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
            last_error = exc
            time.sleep(sleep * (attempt + 1) * 2)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def unix_to_local(value: str | int | None) -> str:
    if value in (None, "", "0"):
        return ""
    try:
        stamp = int(str(value)[:10])
    except ValueError:
        return ""
    zone = dt.timezone(dt.timedelta(hours=8))
    return dt.datetime.fromtimestamp(stamp, zone).strftime("%Y-%m-%d %H:%M:%S %z")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


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


def append_unique(mapping: dict[str, dict[str, Any]], item: dict[str, Any]) -> None:
    key = str(item.get("activity_id") or item.get("id") or "")
    if key and key not in mapping:
        mapping[key] = item


def activity_target_id(activity: dict[str, Any]) -> str:
    target = activity.get("target") or {}
    if isinstance(target, dict) and target.get("id"):
        return str(target["id"])
    targets = activity.get("targets") or []
    if targets and isinstance(targets, list) and isinstance(targets[0], dict):
        return str(targets[0].get("id") or "")
    return ""


def activity_text(activity: dict[str, Any]) -> str:
    target = activity.get("target") or {}
    targets = activity.get("targets") or []
    candidate = target if isinstance(target, dict) else {}
    if not candidate and targets and isinstance(targets, list) and isinstance(targets[0], dict):
        candidate = targets[0]
    return html_to_text(candidate.get("description_html")) or clean_longbridge_markup(candidate.get("description") or "")


def normalize_activity(activity: dict[str, Any]) -> dict[str, Any]:
    target_id = activity_target_id(activity)
    actors = activity.get("actors") or []
    actor = actors[0] if actors else {}
    text = activity_text(activity)
    return {
        "activity_id": str(activity.get("id") or ""),
        "action": activity.get("action") or "",
        "created_at": str(activity.get("created_at") or ""),
        "created_at_local": unix_to_local(activity.get("created_at")),
        "target_id": target_id,
        "target_url": WEB_TOPIC_URL.format(topic_id=target_id) if target_id else "",
        "actor_name": actor.get("name") or "",
        "text": text,
    }


def fetch_profile(member_id: str) -> dict[str, Any]:
    profile_url = f"{BASE_URL}/social/profile?member_id={urllib.parse.quote(member_id)}"
    count_url = f"{BASE_URL}/social/profiles/{urllib.parse.quote(member_id)}/topics_count"
    profile = request_json(profile_url).get("data", {})
    count = request_json(count_url).get("data", {})
    return {"profile": profile, "topics_count": count}


def fetch_activities(member_id: str, sleep: float, max_pages: int | None = None) -> list[dict[str, Any]]:
    activities: dict[str, dict[str, Any]] = {}
    tail_mark = ""
    page = 0
    while True:
        params = {"limit": "25"}
        if tail_mark:
            params["tail_mark"] = tail_mark
        query = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/v2/social/profiles/{urllib.parse.quote(member_id)}/activities?{query}"
        data = request_json(url, sleep=sleep)
        payload = data.get("data") or {}
        page_items = payload.get("activities") or []
        for item in page_items:
            append_unique(activities, normalize_activity(item))
        next_params = payload.get("next_params") or {}
        new_tail = str(next_params.get("tail_mark") or "")
        page += 1
        print(f"activities page={page} items={len(page_items)} unique={len(activities)} tail={new_tail}", file=sys.stderr)
        if not page_items or not new_tail or new_tail == tail_mark:
            break
        if max_pages is not None and page >= max_pages:
            break
        tail_mark = new_tail
        time.sleep(sleep)
    return sorted(activities.values(), key=lambda row: int(row.get("created_at") or 0), reverse=True)


def fetch_incremental_activities(
    member_id: str,
    sleep: float,
    known_activity_ids: set[str],
    max_pages: int | None = None,
) -> list[dict[str, Any]]:
    activities: dict[str, dict[str, Any]] = {}
    tail_mark = ""
    page = 0
    reached_known = False
    while True:
        params = {"limit": "25"}
        if tail_mark:
            params["tail_mark"] = tail_mark
        query = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/v2/social/profiles/{urllib.parse.quote(member_id)}/activities?{query}"
        data = request_json(url, sleep=sleep)
        payload = data.get("data") or {}
        page_items = payload.get("activities") or []
        for item in page_items:
            normalized = normalize_activity(item)
            activity_id = str(normalized.get("activity_id") or "")
            if activity_id and activity_id in known_activity_ids:
                reached_known = True
                break
            append_unique(activities, normalized)
        next_params = payload.get("next_params") or {}
        new_tail = str(next_params.get("tail_mark") or "")
        page += 1
        print(
            f"incremental activities page={page} items={len(page_items)} "
            f"new={len(activities)} reached_known={reached_known} tail={new_tail}",
            file=sys.stderr,
        )
        if reached_known or not page_items or not new_tail or new_tail == tail_mark:
            break
        if max_pages is not None and page >= max_pages:
            break
        tail_mark = new_tail
        time.sleep(sleep)
    return sorted(activities.values(), key=lambda row: int(row.get("created_at") or 0), reverse=True)


def merge_activities(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for item in incoming + existing:
        activity_id = str(item.get("activity_id") or "")
        if activity_id and activity_id not in rows:
            rows[activity_id] = item
    return sorted(rows.values(), key=lambda row: int(row.get("created_at") or 0), reverse=True)


def extract_symbols(topic: dict[str, Any], text: str) -> list[str]:
    symbols: set[str] = set()
    for match in re.finditer(r"\(([A-Z0-9.]{1,10})\.(US|HK|SG|CN)\)", text, re.IGNORECASE):
        symbols.add(match.group(1).upper())
    upper_text = text.upper()
    for alias, symbol in ALIASES.items():
        if alias.upper() in upper_text or alias in text:
            symbols.add(symbol)
    for trend in topic.get("trends") or []:
        counter_id = trend.get("counter_id")
        parts = str(counter_id).split("/")
        if len(parts) >= 3 and not parts[-1].startswith("."):
            symbols.add(parts[-1])
    if not symbols:
        for stock in topic.get("stocks") or []:
            code = stock.get("code")
            if code:
                symbols.add(code)
        for counter_id in topic.get("counter_ids") or []:
            parts = str(counter_id).split("/")
            if len(parts) >= 3:
                code = parts[-1]
                if code.startswith("."):
                    continue
                symbols.add(code)
    return sorted(symbols)


def classify_text(text: str) -> tuple[str, list[str]]:
    tags: list[str] = []
    matched = {}
    for tag, pattern in OPERATION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            tags.append(tag)
            matched[tag] = True
    external_actor = bool(EXTERNAL_ACTOR_PATTERN.search(text))
    self_context = bool(SELF_CONTEXT_PATTERN.search(text))
    self_operation = bool(SELF_OPERATION_PATTERN.search(text))
    if ("buy" in matched or "sell" in matched) and external_actor and not self_context:
        level = "D"
    elif ("buy" in matched or "sell" in matched) and (self_context or self_operation):
        level = "A"
    elif "buy" in matched or "sell" in matched:
        level = "C"
    elif "hold" in matched:
        level = "B"
    elif "watch" in matched or INTENT_PATTERN.search(text):
        level = "C"
    elif EXTERNAL_PATTERN.search(text):
        level = "D"
    else:
        level = "U"
    if EXTERNAL_PATTERN.search(text):
        tags.append("external_info")
    if INTENT_PATTERN.search(text):
        tags.append("thesis")
    return level, sorted(set(tags))


def summarize_action(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.sub(r"不是投资建议[！!。]*", "", compact).strip()
    if len(compact) <= 72:
        return compact
    return compact[:72].rstrip() + "..."


def normalize_topic(topic: dict[str, Any], activity: dict[str, Any] | None = None) -> dict[str, Any]:
    text = html_to_text(topic.get("description_html")) or clean_longbridge_markup(topic.get("description") or "")
    topic_id = str(topic.get("id") or (activity or {}).get("target_id") or "")
    level, tags = classify_text(text)
    symbols = extract_symbols(topic, text)
    images = []
    for image in topic.get("images") or []:
        if isinstance(image, dict):
            images.append(
                {
                    "url": image.get("url") or image.get("src") or "",
                    "original": (image.get("image_style") or {}).get("original") or "",
                    "width": (image.get("meta") or {}).get("width"),
                    "height": (image.get("meta") or {}).get("height"),
                }
            )
    return {
        "topic_id": topic_id,
        "url": WEB_TOPIC_URL.format(topic_id=topic_id) if topic_id else "",
        "activity_id": (activity or {}).get("activity_id", ""),
        "action": (activity or {}).get("action", ""),
        "created_at": str(topic.get("created_at") or (activity or {}).get("created_at") or ""),
        "created_at_local": unix_to_local(topic.get("created_at") or (activity or {}).get("created_at")),
        "updated_at": str(topic.get("updated_at") or ""),
        "updated_at_local": unix_to_local(topic.get("updated_at")),
        "text": text,
        "summary": summarize_action(text),
        "symbols": symbols,
        "counter_ids": topic.get("counter_ids") or [],
        "stocks": [
            {
                "code": stock.get("code"),
                "counter_id": stock.get("counter_id"),
                "name": stock.get("name"),
                "market": stock.get("market"),
            }
            for stock in topic.get("stocks") or []
            if isinstance(stock, dict)
        ],
        "images": images,
        "likes_count": topic.get("likes_count", 0),
        "comments_count": topic.get("comments_count", 0),
        "shares_count": topic.get("shares_count", 0),
        "evidence_level": level,
        "evidence_tags": tags,
    }


def fetch_topic_payload(topic_id: str, sleep: float) -> dict[str, Any] | None:
    paths = [
        f"{BASE_URL}/v2/social/topics/{urllib.parse.quote(topic_id)}",
        f"{BASE_URL}/social/topics/{urllib.parse.quote(topic_id)}",
    ]
    for attempt in range(4):
        for url in paths:
            try:
                data = request_json(url, sleep=sleep)
            except RuntimeError as exc:
                print(f"topic {topic_id} endpoint failed: {exc}", file=sys.stderr)
                continue
            if data.get("code") not in (0, None):
                continue
            topic = (data.get("data") or {}).get("topic")
            if topic:
                return topic
        time.sleep(sleep * (attempt + 1) * 3)
    return None


def fetch_one_topic(topic_id: str, activity: dict[str, Any], sleep: float) -> dict[str, Any] | None:
    topic = fetch_topic_payload(topic_id, sleep)
    if not topic:
        print(f"topic {topic_id} returned no topic payload", file=sys.stderr)
        return None
    return normalize_topic(topic, activity)


def fetch_topics(
    activities: list[dict[str, Any]],
    sleep: float,
    max_topics: int | None = None,
    workers: int = 6,
    existing_topics: list[dict[str, Any]] | None = None,
    checkpoint_path: Path | None = None,
    save_every: int = 50,
) -> list[dict[str, Any]]:
    topic_by_id: dict[str, dict[str, Any]] = {
        str(topic.get("topic_id")): topic
        for topic in (existing_topics or [])
        if topic.get("topic_id")
    }
    topic_ids: list[str] = []
    activity_by_topic: dict[str, dict[str, Any]] = {}
    for activity in activities:
        target_id = activity.get("target_id")
        if target_id and target_id not in activity_by_topic and str(target_id) not in topic_by_id:
            topic_ids.append(str(target_id))
            activity_by_topic[str(target_id)] = activity
    if max_topics is not None:
        topic_ids = topic_ids[:max_topics]
    if not topic_ids:
        return sorted(topic_by_id.values(), key=lambda row: int(row.get("created_at") or 0), reverse=True)
    print(
        f"topics resume_existing={len(topic_by_id)} remaining={len(topic_ids)}",
        file=sys.stderr,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(fetch_one_topic, topic_id, activity_by_topic.get(topic_id, {}), sleep): topic_id
            for topic_id in topic_ids
        }
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            topic_id = futures[future]
            normalized = future.result()
            if normalized:
                topic_by_id[topic_id] = normalized
            if index % 50 == 0 or index == len(topic_ids):
                print(f"topics fetched={index}/{len(topic_ids)} stored={len(topic_by_id)}", file=sys.stderr)
            if checkpoint_path and (index % save_every == 0 or index == len(topic_ids)):
                write_jsonl(
                    checkpoint_path,
                    sorted(topic_by_id.values(), key=lambda row: int(row.get("created_at") or 0), reverse=True),
                )
    return sorted(topic_by_id.values(), key=lambda row: int(row.get("created_at") or 0), reverse=True)


def build_symbol_index(topics: list[dict[str, Any]]) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for topic in topics:
        for symbol in topic.get("symbols") or []:
            entry = index.setdefault(
                symbol,
                {"symbol": symbol, "count": 0, "levels": Counter(), "tags": Counter(), "recent_topics": []},
            )
            entry["count"] += 1
            entry["levels"][topic.get("evidence_level", "U")] += 1
            for tag in topic.get("evidence_tags") or []:
                entry["tags"][tag] += 1
            if len(entry["recent_topics"]) < 12:
                entry["recent_topics"].append(
                    {
                        "date": topic.get("created_at_local", "")[:10],
                        "topic_id": topic.get("topic_id"),
                        "level": topic.get("evidence_level"),
                        "summary": topic.get("summary"),
                        "url": topic.get("url"),
                    }
                )
    for entry in index.values():
        entry["levels"] = dict(entry["levels"])
        entry["tags"] = dict(entry["tags"])
    return dict(sorted(index.items(), key=lambda item: (-item[1]["count"], item[0])))


def build_operation_rows(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for topic in topics:
        level = topic.get("evidence_level")
        if level not in {"A", "B", "C"}:
            continue
        rows.append(
            {
                "date": topic.get("created_at_local", "")[:10],
                "topic_id": topic.get("topic_id"),
                "url": topic.get("url"),
                "level": level,
                "tags": topic.get("evidence_tags") or [],
                "symbols": topic.get("symbols") or [],
                "summary": topic.get("summary"),
            }
        )
    return rows


def write_indexes(
    out_dir: Path,
    profile: dict[str, Any],
    activities: list[dict[str, Any]],
    topics: list[dict[str, Any]],
    member_id: str = DEFAULT_MEMBER_ID,
) -> None:
    operation_rows = build_operation_rows(topics)
    symbol_index = build_symbol_index(topics)
    write_json(out_dir / "profile.json", profile)
    write_jsonl(out_dir / "activities.jsonl", activities)
    write_jsonl(out_dir / "topics.jsonl", topics)
    write_jsonl(out_dir / "operations.jsonl", operation_rows)
    write_json(out_dir / "symbol_index.json", symbol_index)
    generated_at = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S %z")
    dated_topics = [topic for topic in topics if topic.get("created_at_local")]
    first_date = min((topic["created_at_local"] for topic in dated_topics), default="")
    last_date = max((topic["created_at_local"] for topic in dated_topics), default="")
    level_counts = Counter(topic.get("evidence_level", "U") for topic in topics)
    activity_topic_ids = {str(item.get("target_id")) for item in activities if item.get("target_id")}
    stored_topic_ids = {str(item.get("topic_id")) for item in topics if item.get("topic_id")}
    missing_topic_count = len(activity_topic_ids - stored_topic_ids)
    summary = [
        "# ValueGe Longbridge Dataset",
        "",
        f"- Generated at: {generated_at}",
        f"- Member ID: {member_id}",
        f"- Date range: {first_date[:10]} to {last_date[:10]}",
        f"- Activities fetched: {len(activities)}",
        f"- Topics fetched: {len(topics)}",
        f"- Missing topic details: {missing_topic_count}",
        f"- Operation/holding/intent rows: {len(operation_rows)}",
        f"- Symbols indexed: {len(symbol_index)}",
        "- Evidence level counts: "
        f"A={level_counts.get('A', 0)}, "
        f"B={level_counts.get('B', 0)}, "
        f"C={level_counts.get('C', 0)}, "
        f"D={level_counts.get('D', 0)}, "
        f"U={level_counts.get('U', 0)}",
        "",
        "Evidence levels:",
        "",
        "- A: Explicit operation language such as buy, sell, add, trim, clear, build, or option action.",
        "- B: Stated holding status such as core holding, common shares, long hold, non-sellable, or not moving a position.",
        "- C: Intent, watchlist, thesis, or wait-for-opportunity language.",
        "- D: External market information without a clear self-operation.",
        "- U: Unclassified or non-investment content.",
        "",
        "Use `scripts/query_longbridge.py` to search this dataset instead of loading full JSONL files into context.",
    ]
    (out_dir / "dataset-summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--member-id", default=DEFAULT_MEMBER_ID)
    parser.add_argument("--out-dir", default=str(Path(__file__).resolve().parents[1] / "references" / "data"))
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-topics", type=int, default=None)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--activities-only", action="store_true")
    parser.add_argument("--use-existing-activities", action="store_true")
    parser.add_argument("--resume-existing-topics", action="store_true")
    parser.add_argument("--incremental", action="store_true", help="Fetch only activities newer than the local dataset.")
    parser.add_argument("--save-every", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    existing_activities = load_jsonl(out_dir / "activities.jsonl")
    if args.incremental:
        known_activity_ids = {str(item.get("activity_id") or "") for item in existing_activities if item.get("activity_id")}
        new_activities = fetch_incremental_activities(args.member_id, args.sleep, known_activity_ids, args.max_pages)
        if not new_activities:
            print("No new activities found; dataset left unchanged.", file=sys.stderr)
            return 0
        activities = merge_activities(existing_activities, new_activities)
        args.resume_existing_topics = True
        print(f"merged activities existing={len(existing_activities)} new={len(new_activities)} total={len(activities)}", file=sys.stderr)
    elif args.use_existing_activities:
        activities = load_jsonl(out_dir / "activities.jsonl")
        if not activities:
            print("No existing activities found; fetching activities.", file=sys.stderr)
            activities = fetch_activities(args.member_id, args.sleep, args.max_pages)
    else:
        activities = fetch_activities(args.member_id, args.sleep, args.max_pages)
    profile = fetch_profile(args.member_id)
    if args.activities_only:
        write_json(out_dir / "profile.json", profile)
        write_jsonl(out_dir / "activities.jsonl", activities)
        return 0
    existing_topics = load_jsonl(out_dir / "topics.jsonl") if args.resume_existing_topics else []
    topics = fetch_topics(
        activities,
        args.sleep,
        args.max_topics,
        args.workers,
        existing_topics=existing_topics,
        checkpoint_path=out_dir / "topics.jsonl",
        save_every=args.save_every,
    )
    write_indexes(out_dir, profile, activities, topics, member_id=args.member_id)
    print(f"wrote data to {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
