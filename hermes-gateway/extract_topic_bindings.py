#!/usr/bin/env python3
"""
Read-only extract: Office rooms ↔ Telegram forum topics.

Scans Hermes state.db (+ profiles/*/state.db) for topic_bindings rows and
message/timeline metadata. Emits canonical JSON for populate_topic_bindings.py.

No writes. No secrets printed.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

OFFICE_TOPICS = [
    "general",
    "strategy",
    "errors",
    "approvals",
    "tech",
    "creative",
    "content",
    "growth",
    "projects",
    "inbox",
]

DEFAULT_SEED = [
    {"message_thread_id": "1", "topic_title": "general"},
    {"message_thread_id": "4", "topic_title": "strategy"},
    {"message_thread_id": "7", "topic_title": "errors"},
    {"message_thread_id": "10", "topic_title": "approvals"},
    {"message_thread_id": "13", "topic_title": "tech"},
    {"message_thread_id": "16", "topic_title": "creative"},
    {"message_thread_id": "19", "topic_title": "content"},
    {"message_thread_id": "22", "topic_title": "growth"},
    {"message_thread_id": "25", "topic_title": "projects"},
    {"message_thread_id": "28", "topic_title": "inbox"},
]

SLUG_RE = re.compile(r"[^a-z0-9]+")


def office_room_key(topic: str) -> str:
    t = (topic or "").strip().lower()
    if t.startswith("office:"):
        return t
    return f"office:{t}" if t else ""


def slug_topic(value: str) -> str:
    raw = (value or "").strip().lower()
    if raw.startswith("office:"):
        raw = raw.split(":", 1)[1]
    raw = SLUG_RE.sub("-", raw).strip("-")
    # prefer exact office topic if substring match
    if raw in OFFICE_TOPICS:
        return raw
    for t in OFFICE_TOPICS:
        if t in raw.split("-") or raw == t:
            return t
    return raw


def open_ro(path: Path) -> Optional[sqlite3.Connection]:
    if not path.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        return con
    except Exception as exc:
        print(f"warn: cannot open {path}: {exc}", file=sys.stderr)
        return None


def table_names(con: sqlite3.Connection) -> set[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}


def json_dict(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def meta_get(meta: dict, *keys: str) -> str:
    for key in keys:
        val = meta.get(key)
        if val is None:
            continue
        if isinstance(val, dict):
            continue
        text = str(val).strip()
        if text:
            return text
    return ""


def discover_dbs(hermes_home: Path) -> list[Path]:
    paths: list[Path] = []
    root = hermes_home / "state.db"
    if root.exists():
        paths.append(root)
    profiles = hermes_home / "profiles"
    if profiles.is_dir():
        for p in sorted(profiles.iterdir()):
            db = p / "state.db"
            if db.exists():
                paths.append(db)
    # gateway-local timeline copy (dev)
    return paths


def extract_from_topic_bindings(con: sqlite3.Connection, source: str) -> list[dict]:
    tables = table_names(con)
    if "topic_bindings" not in tables:
        return []
    cols = columns(con, "topic_bindings")
    select = ["chat_id", "message_thread_id", "topic_title", "room_key"]
    if "chat_type" in cols:
        select.append("chat_type")
    rows = con.execute(
        f"SELECT {', '.join(select)} FROM topic_bindings"
    ).fetchall()
    out = []
    for row in rows:
        title = slug_topic(row["topic_title"] or "")
        room = office_room_key(row["room_key"] or title)
        if title and room.startswith("office:") and title != room.split(":", 1)[1]:
            # prefer room_key topic if title noisy
            title = room.split(":", 1)[1]
        item = {
            "chat_id": str(row["chat_id"]).strip(),
            "message_thread_id": str(row["message_thread_id"]).strip(),
            "topic_title": title or slug_topic(room),
            "room_key": room or office_room_key(title),
            "chat_type": str(row["chat_type"]).strip()
            if "chat_type" in cols and row["chat_type"]
            else "supergroup",
            "evidence": "topic_bindings",
            "source": source,
            "count": 1,
        }
        if item["chat_id"] and item["message_thread_id"] and item["room_key"]:
            out.append(item)
    return out


def extract_from_messages(con: sqlite3.Connection, source: str) -> list[dict]:
    tables = table_names(con)
    candidates: list[tuple[str, str]] = []
    if "messages" in tables:
        cols = columns(con, "messages")
        if "metadata" in cols:
            candidates.append(("messages", "metadata"))
    if "timeline_events" in tables:
        cols = columns(con, "timeline_events")
        # prefer structured cols if present
        if {"chat_id", "message_thread_id"} <= cols:
            q = """
                SELECT chat_id, message_thread_id, topic_title, room_key, chat_type, metadata
                FROM timeline_events
                WHERE message_thread_id IS NOT NULL AND message_thread_id != ''
                LIMIT 5000
            """
            try:
                rows = con.execute(q).fetchall()
            except Exception:
                rows = []
            out = []
            for row in rows:
                meta = json_dict(row["metadata"] if "metadata" in row.keys() else {})
                chat_id = str(row["chat_id"] or meta_get(meta, "chat_id", "telegram_chat_id") or "").strip()
                thread = str(
                    row["message_thread_id"]
                    or meta_get(meta, "message_thread_id", "thread_id", "topic_id", "forum_topic_id")
                    or ""
                ).strip()
                title = slug_topic(
                    row["topic_title"]
                    or meta_get(meta, "topic_title", "topic", "forum_topic_name")
                    or row["room_key"]
                    or ""
                )
                room = office_room_key(row["room_key"] or title)
                if not chat_id or not thread:
                    continue
                if not room.startswith("office:"):
                    # only keep office-looking topics
                    if title not in OFFICE_TOPICS:
                        continue
                    room = office_room_key(title)
                out.append(
                    {
                        "chat_id": chat_id,
                        "message_thread_id": thread,
                        "topic_title": title if title in OFFICE_TOPICS else room.split(":", 1)[1],
                        "room_key": room,
                        "chat_type": str(row["chat_type"] or meta_get(meta, "chat_type") or "supergroup"),
                        "evidence": "timeline_events",
                        "source": source,
                        "count": 1,
                    }
                )
            return out
        if "metadata" in cols:
            candidates.append(("timeline_events", "metadata"))

    out: list[dict] = []
    for table, meta_col in candidates:
        try:
            rows = con.execute(
                f"SELECT {meta_col} AS metadata FROM {table} LIMIT 8000"
            ).fetchall()
        except Exception:
            continue
        for row in rows:
            meta = json_dict(row["metadata"])
            chat_id = meta_get(meta, "chat_id", "telegram_chat_id")
            thread = meta_get(
                meta, "message_thread_id", "thread_id", "topic_id", "forum_topic_id"
            )
            title = slug_topic(
                meta_get(meta, "topic_title", "topic", "forum_topic_name", "room_key")
            )
            room_raw = meta_get(meta, "room_key")
            room = office_room_key(room_raw or title)
            if not chat_id or not thread:
                continue
            if title not in OFFICE_TOPICS and room.split(":")[-1] not in OFFICE_TOPICS:
                continue
            if room.split(":")[-1] not in OFFICE_TOPICS and title in OFFICE_TOPICS:
                room = office_room_key(title)
            out.append(
                {
                    "chat_id": chat_id,
                    "message_thread_id": thread,
                    "topic_title": title if title in OFFICE_TOPICS else room.split(":", 1)[-1],
                    "room_key": room if room.split(":")[-1] in OFFICE_TOPICS else office_room_key(title),
                    "chat_type": meta_get(meta, "chat_type") or "supergroup",
                    "evidence": f"{table}.metadata",
                    "source": source,
                    "count": 1,
                }
            )
    return out


def merge_bindings(items: Iterable[dict]) -> tuple[list[dict], list[dict]]:
    """Merge by (chat_id, thread) and detect room conflicts."""
    by_thread: dict[tuple[str, str], dict] = {}
    room_to_threads: dict[str, set[tuple[str, str]]] = defaultdict(set)
    conflicts: list[dict] = []

    evidence_rank = {
        "topic_bindings": 3,
        "timeline_events": 2,
        "messages.metadata": 1,
        "timeline_events.metadata": 1,
        "seed": 0,
    }

    for item in items:
        key = (item["chat_id"], item["message_thread_id"])
        room_to_threads[item["room_key"]].add(key)
        prev = by_thread.get(key)
        if not prev:
            by_thread[key] = dict(item)
            continue
        # merge counts + prefer stronger evidence
        prev["count"] = int(prev.get("count") or 0) + int(item.get("count") or 0)
        if evidence_rank.get(item.get("evidence", ""), 0) > evidence_rank.get(
            prev.get("evidence", ""), 0
        ):
            for field in ("topic_title", "room_key", "chat_type", "evidence", "source"):
                if item.get(field):
                    prev[field] = item[field]
        if prev.get("room_key") != item.get("room_key"):
            conflicts.append(
                {
                    "type": "thread_room_mismatch",
                    "chat_id": key[0],
                    "message_thread_id": key[1],
                    "rooms": sorted({prev.get("room_key"), item.get("room_key")}),
                }
            )

    for room, threads in room_to_threads.items():
        if len(threads) > 1:
            conflicts.append(
                {
                    "type": "room_multi_thread",
                    "room_key": room,
                    "threads": sorted(
                        [{"chat_id": c, "message_thread_id": t} for c, t in threads],
                        key=lambda x: x["message_thread_id"],
                    ),
                }
            )

    merged = sorted(
        by_thread.values(),
        key=lambda b: (
            b.get("room_key") or "",
            int(b["message_thread_id"])
            if str(b["message_thread_id"]).isdigit()
            else str(b["message_thread_id"]),
        ),
    )
    return merged, conflicts


def pick_primary_chat(bindings: list[dict], override: Optional[str]) -> str:
    if override:
        return override
    counts: dict[str, int] = defaultdict(int)
    for b in bindings:
        counts[b["chat_id"]] += int(b.get("count") or 1)
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Office↔Telegram topic bindings (read-only)")
    parser.add_argument(
        "--hermes-home",
        default=str(Path.home() / ".hermes"),
        help="Hermes home (default: ~/.hermes; VPS: /root/.hermes)",
    )
    parser.add_argument("--db", action="append", default=[], help="Extra state.db path (repeatable)")
    parser.add_argument("--chat-id", default="", help="Prefer/filter this forum chat_id")
    parser.add_argument(
        "--include-seed",
        action="store_true",
        help="Include hardcoded seed threads as low-priority evidence",
    )
    parser.add_argument("-o", "--output", default="", help="Write JSON to path (else stdout)")
    parser.add_argument("--pretty", action="store_true", default=True)
    args = parser.parse_args()

    hermes_home = Path(args.hermes_home).expanduser()
    dbs = discover_dbs(hermes_home)
    for extra in args.db:
        p = Path(extra).expanduser()
        if p.exists() and p not in dbs:
            dbs.append(p)

    raw: list[dict] = []
    sources: list[str] = []
    for db_path in dbs:
        con = open_ro(db_path)
        if not con:
            continue
        rel = str(db_path)
        sources.append(rel)
        try:
            raw.extend(extract_from_topic_bindings(con, rel))
            raw.extend(extract_from_messages(con, rel))
        finally:
            con.close()

    if args.include_seed:
        chat = args.chat_id or "-1002732623094"
        for seed in DEFAULT_SEED:
            raw.append(
                {
                    "chat_id": chat,
                    "message_thread_id": seed["message_thread_id"],
                    "topic_title": seed["topic_title"],
                    "room_key": office_room_key(seed["topic_title"]),
                    "chat_type": "supergroup",
                    "evidence": "seed",
                    "source": "DEFAULT_SEED",
                    "count": 0,
                }
            )

    if args.chat_id:
        raw = [r for r in raw if r["chat_id"] == args.chat_id] or raw

    bindings, conflicts = merge_bindings(raw)
    primary_chat = pick_primary_chat(bindings, args.chat_id or None)

    # Prefer office-topic rows for primary chat when reporting gaps
    office_bindings = [
        b
        for b in bindings
        if b.get("room_key", "").startswith("office:")
        and (not primary_chat or b["chat_id"] == primary_chat)
        and b.get("topic_title") in OFFICE_TOPICS
    ]
    present = {b["room_key"] for b in office_bindings}
    gaps = [office_room_key(t) for t in OFFICE_TOPICS if office_room_key(t) not in present]

    report = {
        "chat_id": primary_chat,
        "chat_type": "supergroup",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "hermes_home": str(hermes_home),
        "sources": sources,
        "office_topics": OFFICE_TOPICS,
        "bindings": office_bindings or bindings,
        "all_bindings_count": len(bindings),
        "gaps": gaps,
        "conflicts": conflicts,
        "profiles": ["nara", "rafi", "dimas", "sena", "mika", "raka", "tara"],
    }

    text = json.dumps(report, indent=2 if args.pretty else None, ensure_ascii=False)
    if args.output:
        out_path = Path(args.output).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
        print(
            f"wrote {out_path} bindings={len(report['bindings'])} gaps={len(gaps)} conflicts={len(conflicts)}",
            file=sys.stderr,
        )
    else:
        print(text)

    # exit 2 if incomplete (useful for CI/smoke)
    if gaps or conflicts:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
