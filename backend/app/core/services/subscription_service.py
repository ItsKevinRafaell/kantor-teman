"""
Subscription billing helpers.
"""
import uuid
from datetime import datetime, timezone
from calendar import monthrange
from sqlalchemy.orm import Session

from models import Subscription, Wallet, Transaction


def _deduct_due_subscriptions(db: Session) -> list[dict]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    subs = db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.next_billing_date <= today,
    ).all()
    deducted = []
    for sub in subs:
        wallet = db.query(Wallet).filter(Wallet.id == sub.wallet_id).first()
        if not wallet:
            continue
        txn = Transaction(
            wallet_id=sub.wallet_id, type="expense", amount=sub.amount,
            category="Subscription", date=today, notes=f"Auto-deduct: {sub.name}",
        )
        db.add(txn)
        wallet.balance -= sub.amount
        next_date = datetime.strptime(sub.next_billing_date, "%Y-%m-%d")
        if sub.billing_cycle == "monthly":
            next_month = next_date.month % 12 + 1
            next_year = next_date.year + (1 if next_date.month == 12 else 0)
            next_day = min(next_date.day, monthrange(next_year, next_month)[1])
            sub.next_billing_date = f"{next_year}-{next_month:02d}-{next_day:02d}"
        elif sub.billing_cycle == "yearly":
            sub.next_billing_date = f"{next_date.year + 1}-{next_date.month:02d}-{next_date.day:02d}"
        deducted.append({"subscription_id": sub.id, "name": sub.name, "amount": sub.amount})
    db.commit()
    return deducted
