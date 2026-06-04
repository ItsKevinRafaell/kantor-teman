import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from models import Base, engine, SessionLocal, get_db, log_audit, User, Lead, Contact, Project, Proposal, ProposalAnalytics, Transaction, Wallet, Subscription, PaymentMethod, AuditLog, Board, BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist, BoardCardActivity, WorkspaceSheet, WorkspaceColumn, WorkspaceRow, WorkspaceCell, WorkspaceAttachment, DynamicTemplate, Document, DocumentFolder, DocumentTemplate, GeneratedDocument, BrandKit, BrandAsset, DocumentSequence, ServiceItem, Category, Product, ClientNote, ClientCredential, ClientDocument, AdsCampaign, BlastCampaign, BlastMessage, FollowUpSequence, MessageTemplate, ScrapeHistory, LeadActivityLog, LeadAnalysis, AIProxy, ContentProvider, ContentSession, ContentGeneration, SystemSettings, AIModel, ProviderConfig, ContentSchedule
from sqlalchemy import func, select
from schemas import *
from app.core.dependencies import get_current_user, require_admin, _deduct_due_subscriptions
from app.services.finance_service import (
    get_transactions as _svc_get_transactions,
    create_transaction as _svc_create_transaction,
    calculate_financial_summary,
    invalidate_wallet_cache,
)
from app.core.cache import (
    cached, make_request_cache_key,
    invalidate_transaction_cache,
)

router = APIRouter()

@router.get("/api/finance/wallets", response_model=list[WalletOut])
def get_wallets(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(Wallet).all()



@router.post("/api/finance/wallets", response_model=WalletOut, status_code=201)
def create_wallet(body: WalletIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    wallet = Wallet(**body.model_dump())
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet



@router.put("/api/finance/wallets/{wallet_id}", response_model=WalletOut)
def update_wallet(wallet_id: int, body: WalletIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
    wallet.name = body.name
    wallet.balance = body.balance
    wallet.icon = body.icon
    wallet.color = body.color
    db.commit()
    db.refresh(wallet)
    return wallet



@router.delete("/api/finance/wallets/{wallet_id}", status_code=204)
def delete_wallet(wallet_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
    if wallet.transactions or wallet.subscriptions:
        raise HTTPException(status_code=409, detail="Wallet masih memiliki transaksi atau langganan. Arsipkan data terkait terlebih dahulu.")
    db.delete(wallet)
    db.commit()


# ---------------------------------------------------------------------------
# Finance - Transactions
# ---------------------------------------------------------------------------


@router.get("/api/finance/transactions", response_model=list[TransactionOut])
def get_transactions(
    request: Request,
    wallet_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _svc_get_transactions(db, wallet_id=wallet_id, txn_type=type, include_archived=include_archived)



@router.post("/api/finance/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(body: TransactionIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    result = _svc_create_transaction(body, current_user.name, db)
    invalidate_transaction_cache(body.wallet_id)
    return result



@router.put("/api/finance/transactions/{txn_id}", response_model=TransactionOut)
def update_transaction(txn_id: int, body: TransactionIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    if body.type not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="Type harus 'income' atau 'expense'")
    new_wallet = db.query(Wallet).filter(Wallet.id == body.wallet_id).first()
    if not new_wallet:
        raise HTTPException(status_code=404, detail="Wallet tujuan tidak ditemukan")
    wallet = db.query(Wallet).filter(Wallet.id == txn.wallet_id).first()
    if txn.type == "income":
        wallet.balance -= txn.amount
    else:
        wallet.balance += txn.amount
    txn.wallet_id = body.wallet_id
    txn.type = body.type
    txn.amount = body.amount
    txn.category = body.category
    txn.date = body.date
    txn.notes = body.notes
    txn.lead_id = body.lead_id
    txn.is_billed = body.is_billed
    if body.type == "income":
        new_wallet.balance += body.amount
    else:
        new_wallet.balance -= body.amount
    db.commit()
    db.refresh(txn)
    lead_name = None
    if txn.lead_id:
        lead = db.query(Lead).filter(Lead.id == txn.lead_id).first()
        lead_name = lead.business_name if lead else None
    return TransactionOut(
        id=txn.id, wallet_id=txn.wallet_id, type=txn.type, amount=txn.amount,
        category=txn.category, date=txn.date, notes=txn.notes,
        lead_id=txn.lead_id, is_billed=txn.is_billed, lead_name=lead_name,
    )



@router.delete("/api/finance/transactions/{txn_id}", status_code=204)
def delete_transaction(txn_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    if txn.is_archived:
        return
    wallet = db.query(Wallet).filter(Wallet.id == txn.wallet_id).first()
    if txn.type == "income":
        wallet.balance -= txn.amount
    else:
        wallet.balance += txn.amount
    txn.is_archived = True
    txn.deleted_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    log_audit(db, current_user.name, "DELETE", "transactions", txn_id, {"amount": txn.amount, "category": txn.category})
    invalidate_transaction_cache(txn.wallet_id)



@router.post("/api/finance/transactions/restore/{txn_id}", response_model=TransactionOut)
def restore_transaction(txn_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    if not txn.is_archived:
        db.refresh(txn)
        lead_name = txn.lead.business_name if txn.lead else None
        return TransactionOut(
            id=txn.id, wallet_id=txn.wallet_id, type=txn.type, amount=txn.amount,
            category=txn.category, date=txn.date, notes=txn.notes,
            lead_id=txn.lead_id, is_billed=txn.is_billed, lead_name=lead_name,
        )
    wallet = db.query(Wallet).filter(Wallet.id == txn.wallet_id).first()
    if txn.type == "income":
        wallet.balance += txn.amount
    else:
        wallet.balance -= txn.amount
    txn.is_archived = False
    txn.deleted_at = None
    db.commit()
    db.refresh(txn)
    log_audit(db, current_user.name, "RESTORE", "transactions", txn_id, {"amount": txn.amount})
    lead_name = None
    if txn.lead_id:
        lead = db.query(Lead).filter(Lead.id == txn.lead_id).first()
        lead_name = lead.business_name if lead else None
    return TransactionOut(
        id=txn.id, wallet_id=txn.wallet_id, type=txn.type, amount=txn.amount,
        category=txn.category, date=txn.date, notes=txn.notes,
        lead_id=txn.lead_id, is_billed=txn.is_billed, lead_name=lead_name,
    )


# ---------------------------------------------------------------------------
# Finance - Subscriptions
# ---------------------------------------------------------------------------


@router.get("/api/finance/subscriptions", response_model=list[SubscriptionOut])
def get_subscriptions(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    subs = db.query(Subscription).all()
    results = []
    for s in subs:
        wallet = db.query(Wallet).filter(Wallet.id == s.wallet_id).first()
        results.append(SubscriptionOut(
            id=s.id, wallet_id=s.wallet_id, name=s.name, amount=s.amount,
            billing_cycle=s.billing_cycle, next_billing_date=s.next_billing_date,
            is_active=s.is_active, wallet_name=wallet.name if wallet else None,
        ))
    return results



@router.post("/api/finance/subscriptions", response_model=SubscriptionOut, status_code=201)
def create_subscription(body: SubscriptionIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.id == body.wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
    if body.billing_cycle not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="billing_cycle harus 'monthly' atau 'yearly'")
    sub = Subscription(**body.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return SubscriptionOut(
        id=sub.id, wallet_id=sub.wallet_id, name=sub.name, amount=sub.amount,
        billing_cycle=sub.billing_cycle, next_billing_date=sub.next_billing_date,
        is_active=sub.is_active, wallet_name=wallet.name,
    )



@router.put("/api/finance/subscriptions/{sub_id}", response_model=SubscriptionOut)
def update_subscription(sub_id: int, body: SubscriptionIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription tidak ditemukan")
    wallet = db.query(Wallet).filter(Wallet.id == body.wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
    sub.wallet_id = body.wallet_id
    sub.name = body.name
    sub.amount = body.amount
    sub.billing_cycle = body.billing_cycle
    sub.next_billing_date = body.next_billing_date
    sub.is_active = body.is_active
    db.commit()
    db.refresh(sub)
    return SubscriptionOut(
        id=sub.id, wallet_id=sub.wallet_id, name=sub.name, amount=sub.amount,
        billing_cycle=sub.billing_cycle, next_billing_date=sub.next_billing_date,
        is_active=sub.is_active, wallet_name=wallet.name,
    )



@router.delete("/api/finance/subscriptions/{sub_id}", status_code=204)
def delete_subscription(sub_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription tidak ditemukan")
    db.delete(sub)
    db.commit()


# ---------------------------------------------------------------------------
# Finance - Reports
# ---------------------------------------------------------------------------


@router.get("/api/finance/reports", response_model=FinanceReportOut)
def get_finance_reports(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return calculate_financial_summary(db)


# ---------------------------------------------------------------------------
# Finance - Auto-Deduct Subscriptions (Scheduler Endpoint)
# ---------------------------------------------------------------------------

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
            wallet_id=sub.wallet_id,
            type="expense",
            amount=sub.amount,
            category="Subscription",
            date=today,
            notes=f"Auto-deduct: {sub.name}",
        )
        db.add(txn)
        wallet.balance -= sub.amount
        next_date = datetime.strptime(sub.next_billing_date, "%Y-%m-%d")
        if sub.billing_cycle == "monthly":
            from calendar import monthrange
            next_month = next_date.month % 12 + 1
            next_year = next_date.year + (1 if next_date.month == 12 else 0)
            max_day = monthrange(next_year, next_month)[1]
            next_date = next_date.replace(year=next_year, month=next_month, day=min(next_date.day, max_day))
        else:
            from calendar import monthrange
            next_year = next_date.year + 1
            max_day = monthrange(next_year, next_date.month)[1]
            next_date = next_date.replace(year=next_year, day=min(next_date.day, max_day))
        sub.next_billing_date = next_date.strftime("%Y-%m-%d")
        deducted.append({"subscription": sub.name, "amount": sub.amount, "next_billing_date": sub.next_billing_date})
    db.commit()
    return deducted



@router.post("/api/finance/subscriptions/auto-deduct")
def auto_deduct_subscriptions(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    deducted = _deduct_due_subscriptions(db)
    return {"deducted_count": len(deducted), "details": deducted}


# ---------------------------------------------------------------------------
# Finance - Client Unbilled Expenses (for CRM integration)
# ---------------------------------------------------------------------------


@router.get("/api/finance/client/{lead_id}/unbilled")
def get_client_unbilled(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transactions = db.query(Transaction).filter(
        Transaction.lead_id == lead_id,
        Transaction.type == "expense",
        Transaction.is_billed == False,
    ).all()
    total = sum(t.amount for t in transactions)
    return {"lead_id": lead_id, "unbilled_total": total, "count": len(transactions)}


# ---------------------------------------------------------------------------
# Finance - Payment Methods
# ---------------------------------------------------------------------------


@router.get("/api/finance/payment-methods", response_model=list[PaymentMethodOut])
def list_payment_methods(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(PaymentMethod).order_by(PaymentMethod.position, PaymentMethod.id).all()



@router.post("/api/finance/payment-methods", response_model=PaymentMethodOut, status_code=201)
def create_payment_method(body: PaymentMethodIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    pm = PaymentMethod(**body.model_dump())
    db.add(pm)
    db.commit()
    db.refresh(pm)
    return pm



@router.put("/api/finance/payment-methods/{pm_id}", response_model=PaymentMethodOut)
def update_payment_method(pm_id: int, body: PaymentMethodIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    pm = db.query(PaymentMethod).filter(PaymentMethod.id == pm_id).first()
    if not pm:
        raise HTTPException(status_code=404, detail="Metode pembayaran tidak ditemukan")
    for k, v in body.model_dump().items():
        setattr(pm, k, v)
    db.commit()
    db.refresh(pm)
    return pm



@router.delete("/api/finance/payment-methods/{pm_id}", status_code=204)
def delete_payment_method(pm_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    pm = db.query(PaymentMethod).filter(PaymentMethod.id == pm_id).first()
    if not pm:
        raise HTTPException(status_code=404, detail="Metode pembayaran tidak ditemukan")
    db.delete(pm)
    db.commit()



@router.get("/api/finance/outreach-costs")
def get_outreach_costs(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    providers = db.query(ProviderConfig).all()
    provider_list = []
    for p in providers:
        cost_per_unit_idr = p.price_per_unit_idr if p.price_per_unit_idr else (
            ((p.price_input_token_usd + p.price_output_token_usd) / 2) * 1000 * USD_TO_IDR
        )
        provider_list.append({
            "id": p.id,
            "provider_name": p.provider_name,
            "remaining_quota": p.remaining_quota,
            "price_per_unit_idr": p.price_per_unit_idr,
            "price_input_token_usd": p.price_input_token_usd,
            "price_output_token_usd": p.price_output_token_usd,
            "estimated_balance_idr": p.remaining_quota * cost_per_unit_idr if cost_per_unit_idr else 0,
        })

    campaigns = db.query(BlastCampaign).order_by(BlastCampaign.created_at.desc()).all()
    campaign_list = []
    for c in campaigns:
        cost = c.total_operational_cost_idr or 0
        conversions = c.converted_clients_count or 0
        cpa = cost / conversions if conversions > 0 else None
        revenue_estimate = conversions * 5000000
        roi = ((revenue_estimate - cost) / cost * 100) if cost > 0 else None
        campaign_list.append({
            "id": c.id,
            "name": c.name,
            "created_at": c.created_at,
            "sent_count": c.sent_count or 0,
            "total_operational_cost_idr": cost,
            "converted_clients_count": conversions,
            "cpa": cpa,
            "roi": roi,
            "status": c.status,
        })

    return {"providers": provider_list, "campaigns": campaign_list}



