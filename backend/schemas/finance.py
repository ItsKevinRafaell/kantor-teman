from pydantic import BaseModel, Field
from typing import Optional, List


class WalletIn(BaseModel):
    name: str
    balance: float = 0
    icon: Optional[str] = None
    color: Optional[str] = None


class WalletOut(BaseModel):
    id: int
    name: str
    balance: float
    icon: Optional[str] = None
    color: Optional[str] = None
    model_config = {"from_attributes": True}


class TransactionIn(BaseModel):
    wallet_id: int
    type: str  # income / expense
    amount: float
    category: Optional[str] = None
    date: str
    notes: Optional[str] = None
    lead_id: Optional[int] = None
    is_billed: bool = False


class TransactionOut(BaseModel):
    id: int
    wallet_id: int
    type: str
    amount: float
    category: Optional[str] = None
    date: str
    notes: Optional[str] = None
    lead_id: Optional[int] = None
    is_billed: bool
    lead_name: Optional[str] = None
    model_config = {"from_attributes": True}


class SubscriptionIn(BaseModel):
    wallet_id: int
    name: str
    amount: float
    billing_cycle: str = "monthly"
    next_billing_date: str
    is_active: bool = True


class SubscriptionOut(BaseModel):
    id: int
    wallet_id: int
    name: str
    amount: float
    billing_cycle: str
    next_billing_date: str
    is_active: bool
    wallet_name: Optional[str] = None
    model_config = {"from_attributes": True}


class PaymentMethodIn(BaseModel):
    name: str = Field(..., max_length=255)
    account_number: Optional[str] = Field(None, max_length=255)
    account_name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    is_active: bool = True
    position: int = 0


class PaymentMethodOut(BaseModel):
    id: int
    name: str
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    position: int
    model_config = {"from_attributes": True}


class FinanceReportOut(BaseModel):
    total_balance: float
    break_even_point: float
    financial_runway_months: float
    expense_by_category: List[dict]