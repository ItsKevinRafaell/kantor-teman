#!/usr/bin/env python3
"""Import Jago Main Pocket txs Jun 2026 → 21 Jul 2026.

Source: Jago_Main Pocket_History_21072026.pdf
Latest balance 21 Jul 2026: IDR 4.804.824,64

Idempotent via notes containing [JAGO:<id>].
Sets wallet balance to TARGET_BALANCE after import.

Usage (local or SSH host):
  cd backend && python scripts/import_jago_jun_jul_2026.py
  python scripts/import_jago_jun_jul_2026.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from models import SessionLocal, Wallet, Transaction, log_audit  # noqa: E402

WALLET_NAME = "Jago Main Pocket"
TARGET_BALANCE = 4_804_824.64
ACTOR = "import_jago_script"

# (date YYYY-MM-DD, type income|expense, amount, category, notes)
# IDs from PDF when available — used for idempotency [JAGO:<id>]
TXS: list[tuple[str, str, float, str, str, str]] = [
    # date, type, amount, category, note, jago_id
    # ---- June 2026 ----
    ("2026-06-05", "income", 3_503_500.00, "Pemasukan", "Incoming Transfer BCA 3151846911", "3925054053"),
    ("2026-06-06", "expense", 59_413.00, "Tools & Langganan", "QRIS LYNKID Nusapay", "3930440930"),
    ("2026-06-06", "expense", 50_660.00, "Tools & Langganan", "QRIS Pakasir ShopeePay", "3933293904"),
    ("2026-06-07", "expense", 139_000.00, "Tools & Langganan", "QRIS PT ABDI TAWAKAL DUA XENDIT", "3937661721"),
    ("2026-06-08", "expense", 20_097.00, "Tools & Langganan", "QRIS MARKETKU Barang Digital Mandiri", "3941200573"),
    ("2026-06-08", "expense", 35_000.00, "Tools & Langganan", "QRIS Roy Antidonasi Creative GoPay", "3942413940"),
    ("2026-06-08", "expense", 6_000.00, "Tools & Langganan", "QRIS Deal store Grosir GoPay", "3944745581"),
    ("2026-06-08", "expense", 30_000.00, "Transfer", "Outgoing Transfer RENDY SEBPIAN EKA CA Mandiri", "260608JAGBIDJA0023514"),
    ("2026-06-09", "expense", 50_000.00, "Transfer", "Outgoing Transfer RENDY SEBPIAN EKA CA Mandiri", "260609JAGBIDJA0007841"),
    ("2026-06-10", "expense", 25_000.00, "Transfer", "Outgoing Transfer RENDY SEBPIAN EKA CA Mandiri", "260610JAGBIDJA0003334"),
    ("2026-06-10", "expense", 50_660.00, "Tools & Langganan", "QRIS Pakasir ShopeePay", "3953308651"),
    ("2026-06-10", "expense", 50_000.00, "Tools & Langganan", "Outgoing Transfer RADXXXX KEYXX BARXXXX Seabank (up plan entreprise)", "260610JAGBIDJA0008765"),
    ("2026-06-10", "expense", 2_500.00, "Biaya Admin", "Outgoing Transfer Fee", "3954567903"),
    ("2026-06-10", "expense", 25_000.00, "Transfer", "Outgoing Transfer RENDY SEBPIAN EKA CA Mandiri", "260610JAGBIDJA0010697"),
    ("2026-06-10", "expense", 2_500.00, "Biaya Admin", "Outgoing Transfer Fee", "3955007746"),
    ("2026-06-10", "expense", 125_000.00, "Transfer", "Outgoing Transfer RANDOLF TANVERT BCA", "260610JAGBIDJA00197681"),
    ("2026-06-10", "expense", 2_500.00, "Biaya Admin", "Outgoing Transfer Fee", "3957265581"),
    ("2026-06-10", "expense", 35_000.00, "Transfer", "Outgoing Transfer RENDY SEBPIAN EKA CA Mandiri", "260610JAGBIDJA002062C"),
    ("2026-06-10", "expense", 2_500.00, "Biaya Admin", "Outgoing Transfer Fee", "3957499638"),
    ("2026-06-12", "expense", 35_000.00, "Tools & Langganan", "Outgoing Transfer RADXXXX KEYXX BARXXXX Seabank", "260612JAGBIDJA0009608"),
    ("2026-06-12", "expense", 2_500.00, "Biaya Admin", "Outgoing Transfer Fee", "3967535698"),
    ("2026-06-14", "expense", 80_000.00, "Transfer", "Outgoing Transfer RENDY SEBPIAN EKA CA Mandiri", "260614JAGBIDJA0022647"),
    ("2026-06-14", "expense", 2_500.00, "Biaya Admin", "Outgoing Transfer Fee", "3982481264"),
    ("2026-06-18", "expense", 80_000.00, "Transfer", "Outgoing Transfer RANDOLF TANVERT BCA", "260618JAGBIDJA0027453"),
    ("2026-06-18", "expense", 2_500.00, "Biaya Admin", "Outgoing Transfer Fee", "4008208095"),
    ("2026-06-23", "expense", 150_000.00, "Tools & Langganan", "QRIS 9router Digital GoPay", "4038191429"),
    ("2026-06-26", "expense", 30_000.00, "Tools & Langganan", "QRIS Pakasir ShopeePay", "4057734519"),
    ("2026-06-26", "expense", 50_000.00, "Tools & Langganan", "QRIS Mayar XENDIT", "4058322017"),
    ("2026-06-28", "income", 886.61, "Bunga", "Interest MAIN_ACCOUNT", "4084002839"),
    ("2026-06-28", "expense", 177.32, "Biaya Admin", "Tax on Interest", "4084002850"),
    ("2026-06-29", "expense", 260_000.00, "Tools & Langganan", "QRIS Marketing Institute Indon GoPay", "260629-QJHQ-87DCPB"),
    ("2026-06-30", "expense", 25_064.00, "Tools & Langganan", "QRIS WARUNG MBA SAR MTR BRT GoPay", "260630-E7WX-7NQ7YZ"),
    # ---- July 2026 ----
    ("2026-07-01", "expense", 7_359.00, "Tools & Langganan", "QRIS Pakasir ShopeePay", "260701-4ABJ-KCVDH7"),
    ("2026-07-01", "expense", 106_045.00, "Tools & Langganan", "QRIS ZoneID Bank Nobu", "260701-MZHC-VD9C7M"),
    ("2026-07-02", "expense", 150_000.00, "Tools & Langganan", "QRIS 9router Digital GoPay", "260702-JNHK-94VDA9"),
    ("2026-07-03", "income", 3_000.00, "Pemasukan", "QRIS Jago Cashback QRIS Daily Bonus Jun 2026", "260703-ZQDA-6HU2LJ"),
    ("2026-07-04", "income", 500_000.00, "Pemasukan", "Incoming Transfer BCA 3151846911", "260704-Z274-7BERFZ"),
    ("2026-07-06", "expense", 10_070.00, "Tools & Langganan", "QRIS LYNKID Nusapay", "260706-6DLX-H84BUU"),
    ("2026-07-08", "expense", 150_000.00, "Tools & Langganan", "QRIS Roy Antidonasi Creative GoPay", "260708-T2E3-AE6QZY"),
    ("2026-07-08", "income", 3_000_000.00, "Pemasukan", "Incoming Transfer BCA 3151846911", "260708-MFPP-F38XBA"),
    ("2026-07-10", "expense", 65_000.00, "Transfer", "Outgoing Transfer RAHMAT HIDAYAT BCA", "260710JAGBIDJA0009927"),
    ("2026-07-11", "expense", 75_000.00, "Transfer", "Outgoing Transfer DAVID NEHEMIA SUNOTO BCA", "260711JAGBIDJA00245101"),
    ("2026-07-16", "expense", 20_000.00, "Tools & Langganan", "QRIS NUGRAHA STORE DANA", "260716-JQFZ-XDG686"),
    ("2026-07-17", "expense", 40_000.00, "Tools & Langganan", "QRIS NUGRAHA STORE DANA", "260717-ZQX2-HPT4TV"),
    ("2026-07-18", "expense", 4_000.00, "Tools & Langganan", "QRIS Pakasir Pakai Donk", "260718-3A8K-8QZB8Q"),
    ("2026-07-18", "expense", 30_000.00, "Tools & Langganan", "QRIS Roy Antidonasi Creative GoPay", "260718-EREF-93UQ8R"),
    ("2026-07-19", "expense", 100_443.00, "Tools & Langganan", "QRIS Trijaya Indonesia ShopeePay", "260719-F3D6-6VCH92"),
    ("2026-07-19", "expense", 100_443.00, "Tools & Langganan", "QRIS Trijaya Indonesia ShopeePay (2)", "260719-7MMQ-YBYAFL"),
    ("2026-07-19", "income", 100_443.00, "Refund", "QR refund Trijaya Indonesia (QRDO1-R)", "d67dc02a-8d31-42c1-afdf"),
    ("2026-07-20", "expense", 45_000.00, "Tools & Langganan", "QRIS WARUNG MBA SAR MTR BRT GoPay", "260720-ZH4V-4GJ72G"),
    ("2026-07-21", "expense", 20_000.00, "Tools & Langganan", "QRIS NUGRAHA STORE DANA", "260721-VWLU-8JZZNR"),
]


def tag(jago_id: str) -> str:
    return f"[JAGO:{jago_id}]"


def ensure_wallet(db) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.name == WALLET_NAME).first()
    if wallet:
        return wallet
    wallet = Wallet(name=WALLET_NAME, balance=0.0, icon="bank", color="#F97316")
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    print(f"+ created wallet id={wallet.id} name={WALLET_NAME}")
    return wallet


def already_imported(db, wallet_id: int, jago_id: str) -> bool:
    marker = tag(jago_id)
    return (
        db.query(Transaction.id)
        .filter(
            Transaction.wallet_id == wallet_id,
            Transaction.notes.contains(marker),
            Transaction.is_archived == False,
        )
        .first()
        is not None
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-balance-fix", action="store_true", help="Skip forcing wallet.balance to TARGET")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        wallet = ensure_wallet(db)
        created = 0
        skipped = 0
        for date, txn_type, amount, category, note, jago_id in TXS:
            if already_imported(db, wallet.id, jago_id):
                skipped += 1
                continue
            notes = f"{note} {tag(jago_id)}"
            if args.dry_run:
                print(f"DRY {txn_type:7} {amount:>12.2f} {date} {category} | {notes}")
                created += 1
                continue
            txn = Transaction(
                wallet_id=wallet.id,
                type=txn_type,
                amount=float(amount),
                category=category,
                date=date,
                notes=notes,
                is_billed=False,
                is_archived=False,
            )
            db.add(txn)
            if txn_type == "income":
                wallet.balance = float(wallet.balance or 0) + float(amount)
            else:
                wallet.balance = float(wallet.balance or 0) - float(amount)
            created += 1
        if not args.dry_run:
            db.commit()
            if not args.no_balance_fix:
                wallet.balance = TARGET_BALANCE
                db.commit()
                print(f"= wallet.balance forced to {TARGET_BALANCE:,.2f}")
            try:
                log_audit(db, ACTOR, "IMPORT", "transactions", wallet.id, {
                    "source": "jago_main_pocket",
                    "created": created,
                    "skipped": skipped,
                    "target_balance": TARGET_BALANCE,
                })
            except Exception as exc:
                print(f"! audit skip: {exc}")
        print(f"done created={created} skipped={skipped} wallet_id={wallet.id} balance={wallet.balance}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
