"""Finance Service Layer — extracted business logic from routers/finance.py"""
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, select

from models import Transaction, Wallet, Subscription, Lead, log_audit
from schemas import TransactionIn, TransactionOut, FinanceReportOut


# ─── In-memory wallet balance cache (60s TTL, thread-safe) ───────────────────

_wallet_cache: dict[int, tuple[float, float]] = {}  # wallet_id -> (balance, expires_at)
_cache_lock = threading.Lock()


def get_wallet_balance(wallet_id: int, db: Session) -> float:
    """Query wallet balance with 60-second TTL cache."""
    now = time.time()
    with _cache_lock:
        cached = _wallet_cache.get(wallet_id)
        if cached and cached[1] > now:
            return cached[0]

    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    balance = wallet.balance if wallet else 0.0

    with _cache_lock:
        _wallet_cache[wallet_id] = (balance, now + 60)

    return balance


def invalidate_wallet_cache(wallet_id: int) -> None:
    """Clear cache entry when wallet is updated."""
    with _cache_lock:
        _wallet_cache.pop(wallet_id, None)


def invalidate_all_wallet_cache() -> None:
    """Clear all wallet cache entries (used on transaction write)."""
    with _cache_lock:
        _wallet_cache.clear()


# ─── Financial Summary ───────────────────────────────────────────────────────

def calculate_financial_summary(db: Session) -> FinanceReportOut:
    """Aggregate wallet totals, runway, break-even for reports."""
    total_balance = db.query(func.coalesce(func.sum(Wallet.balance), 0)).scalar() or 0

    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    monthly_expenses = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.type == "expense",
        Transaction.date.like(f"{current_month}%"),
        Transaction.is_archived == False,
    ).scalar() or 0

    # Aggregate subscriptions in SQL (fix Python-side loop)
    monthly_total = db.query(func.coalesce(func.sum(Subscription.amount), 0)).filter(
        Subscription.is_active == True,
        Subscription.billing_cycle == "monthly",
    ).scalar() or 0
    yearly_total = db.query(func.coalesce(func.sum(Subscription.amount), 0)).filter(
        Subscription.is_active == True,
        Subscription.billing_cycle == "yearly",
    ).scalar() or 0
    total_subscription_monthly = monthly_total + (yearly_total / 12)

    recorded_subscription_expenses = db.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.type == "expense",
        Transaction.date.like(f"{current_month}%"),
        Transaction.category == "Subscription",
        Transaction.is_archived == False,
    ).scalar() or 0
    subscription_forecast_remaining = max(0, total_subscription_monthly - recorded_subscription_expenses)
    break_even_point = monthly_expenses + subscription_forecast_remaining

    financial_runway = round(total_balance / break_even_point, 1) if break_even_point > 0 else 99.0

    expense_by_category = calculate_expense_by_category(db, current_month)

    return FinanceReportOut(
        total_balance=total_balance,
        break_even_point=break_even_point,
        financial_runway_months=financial_runway,
        expense_by_category=expense_by_category,
    )


def calculate_expense_by_category(db: Session, month: Optional[str] = None) -> list[dict]:
    """Group current-month expenses by category."""
    if month is None:
        month = datetime.now().strftime("%Y-%m")

    category_rows = db.execute(
        select(Transaction.category, func.sum(Transaction.amount).label("total"))
        .where(
            Transaction.type == "expense",
            Transaction.date.like(f"{month}%"),
            Transaction.is_archived == False,
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()

    return [{"category": r[0] or "Lainnya", "amount": r[1]} for r in category_rows]


# ─── Transactions ─────────────────────────────────────────────────────────────

def create_transaction(body: TransactionIn, current_user_name: str, db: Session) -> TransactionOut:
    """Validate, insert transaction, update wallet balance, log audit."""
    wallet = db.query(Wallet).filter(Wallet.id == body.wallet_id).first()
    if not wallet:
        raise ValueError("Wallet tidak ditemukan")

    if body.type not in ("income", "expense"):
        raise ValueError("Type harus 'income' atau 'expense'")

    txn = Transaction(**body.model_dump())
    db.add(txn)

    if body.type == "income":
        wallet.balance += body.amount
    else:
        wallet.balance -= body.amount

    db.commit()
    db.refresh(txn)

    # Invalidate wallet cache
    invalidate_wallet_cache(body.wallet_id)

    log_audit(db, current_user_name, "CREATE", "transactions", txn.id, {
        "type": body.type,
        "amount": body.amount,
        "category": body.category,
    })

    lead_name = None
    if txn.lead_id:
        lead = db.query(Lead).filter(Lead.id == txn.lead_id).first()
        lead_name = lead.business_name if lead else None

    return TransactionOut(
        id=txn.id, wallet_id=txn.wallet_id, type=txn.type, amount=txn.amount,
        category=txn.category, date=txn.date, notes=txn.notes,
        lead_id=txn.lead_id, is_billed=txn.is_billed, lead_name=lead_name,
    )


def get_transactions(
    db: Session,
    wallet_id: Optional[int] = None,
    txn_type: Optional[str] = None,
    include_archived: bool = False,
) -> list[TransactionOut]:
    """Query transactions with optional filters, joined with lead for name."""
    query = db.query(Transaction)
    if not include_archived:
        query = query.filter(Transaction.is_archived == False)
    if wallet_id:
        query = query.filter(Transaction.wallet_id == wallet_id)
    if txn_type:
        query = query.filter(Transaction.type == txn_type)

    transactions = query.options(joinedload(Transaction.lead)).order_by(Transaction.date.desc()).all()

    results = []
    for t in transactions:
        lead_name = t.lead.business_name if t.lead else None
        results.append(TransactionOut(
            id=t.id, wallet_id=t.wallet_id, type=t.type, amount=t.amount,
            category=t.category, date=t.date, notes=t.notes,
            lead_id=t.lead_id, is_billed=t.is_billed, lead_name=lead_name,
        ))
    return results