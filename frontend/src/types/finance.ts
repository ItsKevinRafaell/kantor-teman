// Finance types
export interface WalletData {
  balance: number;
  currency: string;
  last_updated: string;
}

export interface TransactionData {
  id: string;
  type: "income" | "expense";
  amount: number;
  description: string;
  category: string;
  date: string;
  project_id?: string;
  client_id?: number;
}

export interface ReportData {
  total_income: number;
  total_expense: number;
  net_profit: number;
  period: string;
  break_even_point: number;
  financial_runway_months: number;
}

export interface SubscriptionData {
  id: string;
  name: string;
  amount: number;
  billing_cycle: "monthly" | "yearly";
  next_billing_date: string;
  status: "active" | "cancelled" | "paused";
}

export interface PaymentMethod {
  id: string;
  name: string;
  type: "bank" | "ewallet" | "cash";
  account_number?: string;
  account_holder?: string;
  is_default: boolean;
}