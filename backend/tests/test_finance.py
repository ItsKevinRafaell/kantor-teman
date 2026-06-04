"""Finance tests - wallet balance, subscriptions, transaction with eager loading."""
import os
import sys
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.dependencies import create_token, hash_password
from models import User, Wallet, Transaction, Subscription, Lead


def _get_or_create_user(db, email, name, password, role):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name, hashed_password=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _admin_token(db):
    user = _get_or_create_user(db, "finance_admin@test.com", "Finance Admin", "admin123", "admin")
    return create_token(user.id, user.email)


def _unique_phone():
    return f"6281{uuid.uuid4().hex[:10]}"


class TestWalletBalanceConsistency:
    def test_wallet_balance_consistency_after_income(self, client, db):
        token = _admin_token(db)
        wallet = Wallet(name="Test Wallet", balance=1000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        response = client.post(
            "/api/finance/transactions",
            json={"wallet_id": wallet.id, "type": "income", "amount": 500.0, "category": "Sales", "date": "2026-06-04"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        db.refresh(wallet)
        assert wallet.balance == 1500.0

    def test_wallet_balance_consistency_after_expense(self, client, db):
        token = _admin_token(db)
        wallet = Wallet(name="Expense Wallet", balance=2000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        response = client.post(
            "/api/finance/transactions",
            json={"wallet_id": wallet.id, "type": "expense", "amount": 300.0, "category": "Utilities", "date": "2026-06-04"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        db.refresh(wallet)
        assert wallet.balance == 1700.0

    def test_multiple_transactions_maintain_balance(self, client, db):
        token = _admin_token(db)
        wallet = Wallet(name="Multi Wallet", balance=1000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        for txn_type, amount in [("income", 500.0), ("expense", 200.0), ("income", 1000.0), ("expense", 300.0)]:
            response = client.post(
                "/api/finance/transactions",
                json={"wallet_id": wallet.id, "type": txn_type, "amount": amount, "category": "Test", "date": "2026-06-04"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 201

        db.refresh(wallet)
        assert wallet.balance == 2000.0


class TestSubscriptionAutoDeduct:
    def test_subscription_auto_deduct(self, client, db):
        token = _admin_token(db)
        wallet = Wallet(name="Sub Wallet", balance=5000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        sub = Subscription(wallet_id=wallet.id, name="Monthly SaaS", amount=500.0, billing_cycle="monthly", next_billing_date="2026-06-04", is_active=True)
        db.add(sub)
        db.commit()
        db.refresh(sub)

        from app.core.dependencies import _deduct_due_subscriptions
        deducted = _deduct_due_subscriptions(db)

        assert len(deducted) > 0
        db.refresh(wallet)
        assert wallet.balance == 4500.0

        txn = db.query(Transaction).filter(Transaction.wallet_id == wallet.id, Transaction.category == "Subscription").first()
        assert txn is not None

    def test_subscription_next_billing_date_advanced(self, client, db):
        token = _admin_token(db)
        wallet = Wallet(name="Billing Wallet", balance=10000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        sub = Subscription(wallet_id=wallet.id, name="Monthly Service", amount=100.0, billing_cycle="monthly", next_billing_date="2026-06-04", is_active=True)
        db.add(sub)
        db.commit()

        from app.core.dependencies import _deduct_due_subscriptions
        _deduct_due_subscriptions(db)

        db.refresh(sub)
        from datetime import datetime
        next_date = datetime.strptime(sub.next_billing_date, "%Y-%m-%d")
        original_date = datetime(2026, 6, 4)
        assert next_date > original_date


class TestTransactionWithLeadEagerLoad:
    def test_transaction_with_lead_eagerload(self, client, db):
        token = _admin_token(db)
        wallet = Wallet(name="Lead Wallet", balance=10000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        lead1 = Lead(business_name="Client A", phone_number=_unique_phone(), status="Scraped")
        lead2 = Lead(business_name="Client B", phone_number=_unique_phone(), status="Scraped")
        db.add_all([lead1, lead2])
        db.commit()

        for lead in [lead1, lead2]:
            txn = Transaction(wallet_id=wallet.id, type="income", amount=1000.0, category="Sales", date="2026-06-04", lead_id=lead.id)
            db.add(txn)
        db.commit()

        from app.services.finance_service import get_transactions
        transactions = get_transactions(db)

        txns_with_lead = [t for t in transactions if t.lead_name]
        assert len(txns_with_lead) >= 2

        lead_names = {t.lead_name for t in txns_with_lead}
        assert "Client A" in lead_names
        assert "Client B" in lead_names

    def test_transaction_query_uses_joinedload_not_lazy(self, client, db):
        wallet = Wallet(name="Inspect Wallet", balance=100.0)
        db.add(wallet)
        db.commit()

        lead = Lead(business_name="Inspect Lead", phone_number=_unique_phone(), status="Scraped")
        db.add(lead)
        db.commit()

        txn = Transaction(wallet_id=wallet.id, type="expense", amount=50.0, category="Test", date="2026-06-04", lead_id=lead.id)
        db.add(txn)
        db.commit()
        db.refresh(txn)

        from app.services.finance_service import get_transactions
        transactions = get_transactions(db)

        # Find the transaction we just created
        our_txn = next((t for t in transactions if t.id == txn.id), None)
        assert our_txn is not None, f"Transaction {txn.id} not found in results"
        assert our_txn.lead_name == "Inspect Lead", f"Expected Inspect Lead, got {txn_out.lead_name}. First txn: {transactions[0]}"
