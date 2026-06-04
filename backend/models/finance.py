from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    balance = Column(Float, nullable=False, default=0)
    icon = Column(String(255), nullable=True)
    color = Column(String(255), nullable=True)
    transactions = relationship("Transaction", back_populates="wallet")
    subscriptions = relationship("Subscription", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    type = Column(String(255), nullable=False)  # income / expense
    amount = Column(Float, nullable=False)
    category = Column(String(255), nullable=True)
    date = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    is_billed = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    deleted_at = Column(String(255), nullable=True)
    wallet = relationship("Wallet", back_populates="transactions")
    lead = relationship("Lead", foreign_keys=[lead_id])


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    billing_cycle = Column(String(255), nullable=False, default="monthly")  # monthly / yearly
    next_billing_date = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    wallet = relationship("Wallet", back_populates="subscriptions")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Bank BCA", "GoPay"
    account_number = Column(String(255), nullable=True)  # rekening / nomor
    account_name = Column(String(255), nullable=True)  # atas nama
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    position = Column(Integer, default=0)
