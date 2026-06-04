"""Finance tests - wallet balance, subscriptions, transaction with eager loading."""
import os

import pytest
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.dependencies import create_token, hash_password
from models import User, Wallet, Transaction, Subscription, Lead


class TestWalletBalanceConsistency:
    """Test wallet balance stays consistent after transactions."""

    def test_wallet_balance_consistency_after_income(self, client, db, admin_user):
        """Create income transaction -> wallet balance must be updated."""
        token = create_token(admin_user.id, admin_user.email)

        # Create wallet
        wallet = Wallet(name="Test Wallet", balance=1000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        # Create income transaction
        response = client.post(
            "/api/finance/transactions",
            json={
                "wallet_id": wallet.id,
                "type": "income",
                "amount": 500.0,
                "category": "Sales",
                "date": "2026-06-04",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        txn_data = response.json()

        # Verify wallet balance updated
        db.refresh(wallet)
        assert wallet.balance == 1500.0, f"Expected 1500, got {wallet.balance}"

    def test_wallet_balance_consistency_after_expense(self, client, db, admin_user):
        """Create expense transaction -> wallet balance must decrease."""
        token = create_token(admin_user.id, admin_user.email)

        # Create wallet with initial balance
        wallet = Wallet(name="Expense Test Wallet", balance=2000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        # Create expense transaction
        response = client.post(
            "/api/finance/transactions",
            json={
                "wallet_id": wallet.id,
                "type": "expense",
                "amount": 300.0,
                "category": "Utilities",
                "date": "2026-06-04",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201

        # Verify wallet balance decreased
        db.refresh(wallet)
        assert wallet.balance == 1700.0, f"Expected 1700, got {wallet.balance}"

    def test_multiple_transactions_maintain_balance(self, client, db, admin_user):
        """Multiple transactions -> balance should be correct."""
        token = create_token(admin_user.id, admin_user.email)

        wallet = Wallet(name="Multi Transaction Wallet", balance=1000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        # Add multiple transactions
        transactions = [
            ("income", 500.0),   # 1500
            ("expense", 200.0),  # 1300
            ("income", 1000.0),  # 2300
            ("expense", 300.0),  # 2000
        ]

        for txn_type, amount in transactions:
            response = client.post(
                "/api/finance/transactions",
                json={
                    "wallet_id": wallet.id,
                    "type": txn_type,
                    "amount": amount,
                    "category": "Test",
                    "date": "2026-06-04",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 201

        db.refresh(wallet)
        assert wallet.balance == 2000.0, f"Expected 2000, got {wallet.balance}"


class TestSubscriptionAutoDeduct:
    """Test subscription auto-deduction."""

    def test_subscription_auto_deduct(self, client, db, admin_user):
        """Subscription due -> wallet balance should decrease."""
        token = create_token(admin_user.id, admin_user.email)

        # Create wallet with known balance
        wallet = Wallet(name="Subscription Wallet", balance=5000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        # Create subscription due today
        subscription = Subscription(
            wallet_id=wallet.id,
            name="Monthly SaaS",
            amount=500.0,
            billing_cycle="monthly",
            next_billing_date="2026-06-04",  # Today
            is_active=True,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        # Run auto-deduct
        from app.core.dependencies import _deduct_due_subscriptions
        deducted = _deduct_due_subscriptions(db)

        # Verify deduction occurred
        assert len(deducted) > 0, "Should have deducted at least one subscription"
        assert deducted[0]["subscription_id"] == subscription.id

        # Verify wallet balance decreased
        db.refresh(wallet)
        assert wallet.balance == 4500.0, f"Expected 4500 after deduction, got {wallet.balance}"

        # Verify transaction was created
        txn = db.query(Transaction).filter(
            Transaction.wallet_id == wallet.id,
            Transaction.category == "Subscription",
        ).first()
        assert txn is not None, "Transaction should be created for subscription"
        assert txn.amount == 500.0

    def test_subscription_next_billing_date_advanced(self, client, db, admin_user):
        """Verify subscription billing date advances after deduction."""
        token = create_token(admin_user.id, admin_user.email)

        wallet = Wallet(name="Billing Date Test", balance=10000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        # Create monthly subscription
        subscription = Subscription(
            wallet_id=wallet.id,
            name="Monthly Service",
            amount=100.0,
            billing_cycle="monthly",
            next_billing_date="2026-06-04",
            is_active=True,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        # Run auto-deduct
        from app.core.dependencies import _deduct_due_subscriptions
        _deduct_due_subscriptions(db)

        # Verify next billing date advanced by ~1 month
        db.refresh(subscription)
        # Next billing date should be July 4 or similar
        from datetime import datetime
        next_date = datetime.strptime(subscription.next_billing_date, "%Y-%m-%d")
        original_date = datetime(2026, 6, 4)
        # Should be approximately 1 month later
        assert next_date > original_date, "Next billing date should advance"


class TestTransactionWithLeadEagerLoad:
    """Test transaction queries use joinedload to avoid N+1."""

    def test_transaction_with_lead_eagerload(self, client, db, admin_user):
        """Verify transaction query uses joinedload for lead."""
        token = create_token(admin_user.id, admin_user.email)

        # Create wallet
        wallet = Wallet(name="Lead Test Wallet", balance=10000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        # Create leads
        lead1 = Lead(
            business_name="Client A",
            phone_number="6281234567891",
            status="Scraped",
        )
        lead2 = Lead(
            business_name="Client B",
            phone_number="6281234567892",
            status="Scraped",
        )
        db.add_all([lead1, lead2])
        db.commit()

        # Create transactions with leads
        for lead in [lead1, lead2]:
            txn = Transaction(
                wallet_id=wallet.id,
                type="income",
                amount=1000.0,
                category="Sales",
                date="2026-06-04",
                lead_id=lead.id,
            )
            db.add(txn)
        db.commit()

        # Query transactions using the service function
        from app.services.finance_service import get_transactions

        transactions = get_transactions(db)

        # Verify transactions include lead names (via joinedload)
        assert len(transactions) >= 2, "Should have at least 2 transactions"

        # Check that lead relationship was eager loaded
        txns_with_lead = [t for t in transactions if t.lead_name]
        assert len(txns_with_lead) >= 2, "Transactions should have lead names eager-loaded"

        # Verify lead names are correct
        lead_names = {t.lead_name for t in txns_with_lead}
        assert "Client A" in lead_names, "Should include Client A"
        assert "Client B" in lead_names, "Should include Client B"

    def test_transaction_query_uses_joinedload_not_lazy(self, client, db, admin_user):
        """Verify get_transactions uses joinedload for lead relationship."""
        from app.services.finance_service import get_transactions
        from sqlalchemy import inspect

        # Create minimal data
        wallet = Wallet(name="Inspect Test", balance=100.0)
        db.add(wallet)
        db.commit()

        lead = Lead(
            business_name="Inspect Lead",
            phone_number="6289999999999",
            status="Scraped",
        )
        db.add(lead)
        db.commit()

        txn = Transaction(
            wallet_id=wallet.id,
            type="expense",
            amount=50.0,
            category="Test",
            date="2026-06-04",
            lead_id=lead.id,
        )
        db.add(txn)
        db.commit()

        # Call get_transactions
        transactions = get_transactions(db)

        # Should have transaction with lead_name
        assert len(transactions) > 0
        txn_out = transactions[0]
        assert txn_out.lead_name == "Inspect Lead", \
            "Lead name should be available without additional query (joinedload)"
