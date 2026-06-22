#!/usr/bin/env python3
"""
Populate initial topic bindings for Telegram mirror.
This script creates the bindings between Telegram topics and office rooms.
"""
import sqlite3
import json

# Topic bindings discovered from Telegram
BINDINGS = [
    {"chat_id": "-1002732623094", "message_thread_id": "1", "topic_title": "general", "room_key": "office:general"},
    {"chat_id": "-1002732623094", "message_thread_id": "4", "topic_title": "strategy", "room_key": "office:strategy"},
    {"chat_id": "-1002732623094", "message_thread_id": "7", "topic_title": "errors", "room_key": "office:errors"},
    {"chat_id": "-1002732623094", "message_thread_id": "10", "topic_title": "approvals", "room_key": "office:approvals"},
    {"chat_id": "-1002732623094", "message_thread_id": "13", "topic_title": "tech", "room_key": "office:tech"},
    {"chat_id": "-1002732623094", "message_thread_id": "16", "topic_title": "creative", "room_key": "office:creative"},
    {"chat_id": "-1002732623094", "message_thread_id": "19", "topic_title": "content", "room_key": "office:content"},
    {"chat_id": "-1002732623094", "message_thread_id": "22", "topic_title": "growth", "room_key": "office:growth"},
    {"chat_id": "-1002732623094", "message_thread_id": "25", "topic_title": "projects", "room_key": "office:projects"},
    {"chat_id": "-1002732623094", "message_thread_id": "28", "topic_title": "inbox", "room_key": "office:inbox"},
]

DB_PATH = "/root/.hermes/state.db"

def main():
    print(f"Connecting to {DB_PATH}...")
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Create topic_bindings table if it doesn't exist
    print("Creating topic_bindings table...")
    con.execute("""
        CREATE TABLE IF NOT EXISTS topic_bindings (
            chat_id TEXT NOT NULL,
            message_thread_id TEXT NOT NULL,
            topic_title TEXT NOT NULL,
            room_key TEXT NOT NULL,
            PRIMARY KEY (chat_id, message_thread_id)
        )
    """)
    con.commit()

    # Insert all bindings
    print(f"Inserting {len(BINDINGS)} topic bindings...")
    for binding in BINDINGS:
        con.execute("""
            INSERT INTO topic_bindings (chat_id, message_thread_id, topic_title, room_key)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, message_thread_id)
            DO UPDATE SET topic_title = excluded.topic_title, room_key = excluded.room_key
        """, (binding["chat_id"], binding["message_thread_id"], binding["topic_title"], binding["room_key"]))
        print(f"  ✓ {binding['topic_title']} -> {binding['room_key']}")

    con.commit()

    # Verify bindings
    rows = con.execute("SELECT * FROM topic_bindings ORDER BY message_thread_id").fetchall()
    print(f"\n✓ Successfully created {len(rows)} topic bindings:")
    for row in rows:
        print(f"  {row['topic_title']}: thread={row['message_thread_id']}, room={row['room_key']}")

    con.close()
    print("\n✓ Done!")

if __name__ == "__main__":
    main()
