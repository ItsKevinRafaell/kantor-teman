// Lead types
export type LeadStatus = "Scraped" | "Contacted" | "Replied" | "Closed/Lost" | "Closed/Client";

export const LEAD_STATUSES: LeadStatus[] = ["Scraped", "Contacted", "Replied", "Closed/Lost", "Closed/Client"];

export const STATUS_COLORS: Record<LeadStatus, string> = {
  Scraped: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  Contacted: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  Replied: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  "Closed/Lost": "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  "Closed/Client": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
};

export interface Lead {
  id: number;
  business_name: string;
  phone_number: string;
  address: string | null;
  original_url: string | null;
  status: LeadStatus;
  product_interest: string | null;
  batch_name: string | null;
  rating: number;
  is_archived: boolean;
  deleted_at: string | null;
  lead_score: number;
  action_recommendation?: string;
  is_ghost_viewer: boolean;
  website_url?: string | null;
  google_rating?: number | null;
  review_count?: number | null;
  sales_owner?: string | null;
  next_action_at?: string | null;
  loss_reason?: string | null;
  do_not_contact: boolean;
}

export type LeadMap = Record<number, Lead>;

export interface SelectedService {
  id: string;
  name: string;
  price: number;
  features: string;
}