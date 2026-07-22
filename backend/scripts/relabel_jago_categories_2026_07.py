#!/usr/bin/env python3
"""Relabel bulk Jago transaction categories to Indonesian display labels.

Idempotent. Safe to re-run.

Mapping:
  food      → Makanan
  tools     → Tools & Langganan
  income    → Pemasukan
  transfer  → Transfer
  fee       → Biaya Admin
  interest  → Bunga
  notes ~ /refund/i → Refund (keeps type as-is, usually income)

Usage:
  cd backend && python scripts/relabel_jago_categories_2026_07.py --dry-run
  cd backend && python scripts/relabel_jago_categories_2026_07.py
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from models import SessionLocal, Transaction, log_audit  # noqa: E402

CATEGORY_MAP = {
    "food": "Makanan",
    "tools": "Tools & Langganan",
    "income": "Pemasukan",
    "transfer": "Transfer",
    "fee": "Biaya Admin",
    "interest": "Bunga",
    # already-nice aliases (no-op if same)
    "makanan": "Makanan",
    "tools & langganan": "Tools & Langganan",
    "pemasukan": "Pemasukan",
    "biaya admin": "Biaya Admin",
    "bunga": "Bunga",
    "refund": "Refund",
}

ACTOR = "relabel_jago_categories_2026_07"


def normalize_key(value: str | None) -> str:
    return (value or "").strip().lower()


def target_category(category: str | None, notes: str | None) -> str | None:
    notes_l = (notes or "").lower()
    if "refund" in notes_l:
        return "Refund"
    key = normalize_key(category)
    if not key:
        return None
    if key in CATEGORY_MAP:
        return CATEGORY_MAP[key]
    # Title-case free-text leftovers only if all-lowercase english-ish slug
    if key == category and " " not in key and key.isalpha():
        return category[:1].upper() + category[1:]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    updated = 0
    skipped = 0
    try:
        rows = db.query(Transaction).all()
        for txn in rows:
            new_cat = target_category(txn.category, txn.notes)
            if not new_cat or new_cat == txn.category:
                skipped += 1
                continue
            print(f"  #{txn.id}: {txn.category!r} → {new_cat!r} | {(txn.notes or '')[:60]}")
            if not args.dry_run:
                old = txn.category
                txn.category = new_cat
                log_audit(
                    db,
                    ACTOR,
                    "UPDATE",
                    "transactions",
                    txn.id,
                    {"category_from": old, "category_to": new_cat},
                )
            updated += 1
        if not args.dry_run:
            db.commit()
        print(f"{'[dry-run] ' if args.dry_run else ''}updated={updated} skipped={skipped}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
