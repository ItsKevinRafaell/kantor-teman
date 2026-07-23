#!/usr/bin/env python3
"""
Upsert Office rooms ↔ Telegram forum topic bindings into Hermes state.db.

Prefer extract_topic_bindings.py JSON over hardcoded seed.
Default is dry-run; pass --apply to write.

Schema aligns with timeline_service.init_sync_db (includes chat_type).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional

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

# Discovered historically; re-extract on VPS before apply if topics recreated.
DEFAULT_CHAT_ID = "-1002732623094"
DEFAULT_BINDINGS = [
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

PROFILES = ["nara", "rafi", "dimas", "sena", "mika", "raka", "tara"]


def office_room_key(topic: str) -> str:
    t = (topic or "").strip().lower()
    if t.startswith("office:"):
        return t
    return f"office:{t}"


def normalize_binding(raw: dict[str, Any], default_chat_id: str, chat_type: str) -> Optional[dict]:
    chat_id = str(raw.get("chat_id") or default_chat_id or "").strip()
    thread = str(raw.get("message_thread_id") or "").strip()
    title = str(raw.get("topic_title") or "").strip().lower()
    room = str(raw.get("room_key") or "").strip().lower()
    if room.startswith("office:"):
        title = title or room.split(":", 1)[1]
    elif title:
        room = office_room_key(title)
    else:
        return None
    if not room.startswith("office:"):
        room = office_room_key(room)
    title = title or room.split(":", 1)[1]
    if not chat_id or not thread or not title:
        return None
    return {
        "chat_id": chat_id,
        "message_thread_id": thread,
        "topic_title": title,
        "room_key": room,
        "chat_type": str(raw.get("chat_type") or chat_type or "supergroup").strip(),
    }


def load_bindings(args: argparse.Namespace) -> tuple[list[dict], list[str], list[dict]]:
    gaps: list[str] = []
    conflicts: list[dict] = []
    chat_id = args.chat_id or DEFAULT_CHAT_ID
    chat_type = args.chat_type

    if args.from_json:
        path = Path(args.from_json).expanduser()
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            chat_id = args.chat_id or data.get("chat_id") or chat_id
            chat_type = args.chat_type or data.get("chat_type") or chat_type
            raw_list = data.get("bindings") or []
            gaps = list(data.get("gaps") or [])
            conflicts = list(data.get("conflicts") or [])
        elif isinstance(data, list):
            raw_list = data
        else:
            raise SystemExit(f"unsupported JSON shape in {path}")
    else:
        raw_list = [
            {
                "chat_id": chat_id,
                "message_thread_id": b["message_thread_id"],
                "topic_title": b["topic_title"],
                "room_key": office_room_key(b["topic_title"]),
                "chat_type": chat_type,
            }
            for b in DEFAULT_BINDINGS
        ]

    bindings: list[dict] = []
    for raw in raw_list:
        item = normalize_binding(raw, chat_id, chat_type)
        if item:
            if args.chat_id:
                item["chat_id"] = args.chat_id
            bindings.append(item)

    # de-dupe by thread pk
    by_pk: dict[tuple[str, str], dict] = {}
    for b in bindings:
        by_pk[(b["chat_id"], b["message_thread_id"])] = b
    bindings = sorted(
        by_pk.values(),
        key=lambda b: int(b["message_thread_id"])
        if b["message_thread_id"].isdigit()
        else b["message_thread_id"],
    )

    present = {b["room_key"] for b in bindings}
    if not gaps:
        gaps = [office_room_key(t) for t in OFFICE_TOPICS if office_room_key(t) not in present]
    return bindings, gaps, conflicts


def ensure_schema(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS topic_bindings (
            chat_id TEXT NOT NULL,
            message_thread_id TEXT NOT NULL,
            topic_title TEXT NOT NULL,
            room_key TEXT NOT NULL,
            chat_type TEXT NOT NULL DEFAULT 'private',
            PRIMARY KEY (chat_id, message_thread_id)
        )
        """
    )
    cols = {r[1] for r in con.execute("PRAGMA table_info(topic_bindings)")}
    if "chat_type" not in cols:
        con.execute(
            "ALTER TABLE topic_bindings ADD COLUMN chat_type TEXT NOT NULL DEFAULT 'private'"
        )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_topic_bindings_room_key ON topic_bindings(room_key)"
    )
    con.commit()


def upsert(con: sqlite3.Connection, bindings: list[dict]) -> None:
    for b in bindings:
        con.execute(
            """
            INSERT INTO topic_bindings
                (chat_id, message_thread_id, topic_title, room_key, chat_type)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, message_thread_id)
            DO UPDATE SET
                topic_title = excluded.topic_title,
                room_key = excluded.room_key,
                chat_type = excluded.chat_type
            """,
            (
                b["chat_id"],
                b["message_thread_id"],
                b["topic_title"],
                b["room_key"],
                b["chat_type"],
            ),
        )
    con.commit()


def resolve_targets(args: argparse.Namespace) -> list[Path]:
    targets: list[Path] = []
    if args.db:
        targets.append(Path(args.db).expanduser())
    else:
        env = os.getenv("HERMES_STATE_DB", "").strip()
        if env:
            targets.append(Path(env).expanduser())
        else:
            # VPS default (gateway SYNC_DB); local fallback ~/.hermes/state.db
            vps = Path("/root/.hermes/state.db")
            local = Path.home() / ".hermes" / "state.db"
            targets.append(vps if vps.parent.exists() or os.geteuid() == 0 else local)

    if args.profiles_all:
        home = Path(args.hermes_home).expanduser()
        for name in PROFILES:
            p = home / "profiles" / name / "state.db"
            if p.exists():
                targets.append(p)
            else:
                print(f"warn: profile db missing (skip): {p}", file=sys.stderr)

    # unique preserve order
    seen: set[str] = set()
    out: list[Path] = []
    for t in targets:
        key = str(t)
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def print_plan(bindings: list[dict], gaps: list[str], conflicts: list[dict], targets: list[Path]) -> None:
    print("=== topic bindings plan ===")
    print(f"targets ({len(targets)}):")
    for t in targets:
        print(f"  - {t}")
    print(f"bindings ({len(bindings)}):")
    for b in bindings:
        print(
            f"  {b['topic_title']:10} thread={b['message_thread_id']:>4} "
            f"room={b['room_key']} chat={b['chat_id']} type={b['chat_type']}"
        )
    if gaps:
        print(f"gaps ({len(gaps)}): {', '.join(gaps)}")
    if conflicts:
        print(f"conflicts ({len(conflicts)}):")
        for c in conflicts:
            print(f"  {c}")
    print("===========================")


def verify(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute(
        """
        SELECT chat_id, message_thread_id, topic_title, room_key, chat_type
        FROM topic_bindings
        ORDER BY CAST(message_thread_id AS INTEGER), message_thread_id
        """
    ).fetchall()


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate topic_bindings (Office↔Telegram)")
    parser.add_argument("--from-json", default="", help="JSON from extract_topic_bindings.py")
    parser.add_argument("--db", default="", help="Target state.db (default HERMES_STATE_DB or /root/.hermes/state.db)")
    parser.add_argument("--hermes-home", default="/root/.hermes", help="For --profiles-all")
    parser.add_argument("--profiles-all", action="store_true", help="Also upsert into profiles/*/state.db if present")
    parser.add_argument("--chat-id", default="", help="Override forum chat_id")
    parser.add_argument("--chat-type", default="supergroup")
    parser.add_argument("--dry-run", action="store_true", help="Plan only (default if --apply omitted)")
    parser.add_argument("--apply", action="store_true", help="Write changes")
    parser.add_argument("--force", action="store_true", help="Apply even with gaps/conflicts")
    args = parser.parse_args()

    # dry-run default unless --apply
    dry = (not args.apply) or args.dry_run
    if args.apply and args.dry_run:
        print("error: use either --apply or --dry-run", file=sys.stderr)
        return 1

    try:
        bindings, gaps, conflicts = load_bindings(args)
    except Exception as exc:
        print(f"error loading bindings: {exc}", file=sys.stderr)
        return 1

    if not bindings:
        print("error: no bindings to apply", file=sys.stderr)
        return 1

    targets = resolve_targets(args)
    print_plan(bindings, gaps, conflicts, targets)

    if (gaps or conflicts) and args.apply and not args.force:
        print(
            "refusing --apply: gaps/conflicts present (re-extract, fix JSON, or pass --force)",
            file=sys.stderr,
        )
        return 2

    if dry:
        print("dry-run: no writes")
        return 2 if gaps or conflicts else 0

    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"writing {target} ...")
        con = sqlite3.connect(str(target), timeout=10)
        con.row_factory = sqlite3.Row
        try:
            ensure_schema(con)
            upsert(con, bindings)
            rows = verify(con)
            print(f"  ok rows={len(rows)}")
            for row in rows:
                print(
                    f"  ✓ {row['topic_title']}: thread={row['message_thread_id']}, "
                    f"room={row['room_key']}"
                )
        finally:
            con.close()

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
