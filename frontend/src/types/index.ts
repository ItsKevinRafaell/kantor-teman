// Shared Types - Barrel Export

// Contact types
export type { Contact, ProjectData, ServiceItem, ProductItem } from "./contact";

// Lead types
export type { Lead, LeadStatus, LeadMap, SelectedService } from "./lead";
export { LEAD_STATUSES, STATUS_COLORS } from "./lead";

// Finance types
export type { WalletData, TransactionData, ReportData, SubscriptionData, PaymentMethod } from "./finance";

// Proposal types
export type { ProposalRecord, TimelinePhase, ProposalAnalytics, ProposalSuccess, TimelineTemplate } from "./proposal";

// Campaign types
export type { Campaign, ProviderData, CampaignCost, BlastTemplate, FollowUpTemplate } from "./campaign";

// Common UI types
export interface ToastMessage {
  message: string;
  type: "success" | "error" | "info";
}

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

export interface ModalState<T = unknown> {
  open: boolean;
  data: T | null;
}

export interface DeleteModalState {
  open: boolean;
  id: number | string | null;
  name: string;
}

// Activity timeline
export interface TimelineEvent {
  type: string;
  icon: string;
  label: string;
  timestamp: string;
}

// Client notes
export interface ClientNote {
  id: string;
  category: "BISNIS" | "TEKNIS" | "PENTING";
  content: string;
  actor: string;
  timestamp: string;
}

// Service type option
export interface ServiceTypeOption {
  value: string;
  label: string;
  default_months: number;
}

// API Response types
export interface ApiError {
  detail: string;
}

export interface ApiSuccess<T> {
  data: T;
  message?: string;
}

// Dashboard analytics
export interface Analytics {
  total_leads: number;
  total_clients: number;
  conversion_rate: number;
  leads_by_product: { product: string; count: number }[];
  leads_by_status: { status: string; count: number }[];
}

export interface Patterns {
  by_category: { segment: string; total: number; converted: number; rate: number }[];
  by_city: { segment: string; total: number; converted: number; rate: number }[];
  by_rating: { segment: string; total: number; converted: number; rate: number }[];
  recommendation: string;
}

export interface BoardOverview {
  project_id: string;
  overdue_cards: string[];
  due_soon_cards: string[];
}

export interface FinanceOverview {
  total_balance: number;
  break_even_point: number;
  financial_runway_months: number;
}

// Hot leads
export interface HotLead {
  lead_id: number;
  business_name: string;
  phone_number: string;
  category: string | null;
  status: "online" | "recent" | "inactive";
  last_active: string;
  total_opens: number;
  proposal_slug: string | null;
}

// Top scored lead
export interface TopScoredLead {
  id: number;
  business_name: string;
  phone_number: string;
  lead_score: number;
  status: string;
  product_interest: string | null;
  address: string | null;
}

// Re-engagement alert
export interface ReengagementAlert {
  id: string;
  lead_id: number;
  business_name: string;
  phone_number: string;
  category: string | null;
  triggered_at: string;
  days_since_first_view: number;
  proposal_slug: string | null;
}