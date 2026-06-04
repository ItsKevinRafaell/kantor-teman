// Campaign types
export interface Campaign {
  id: string;
  name: string;
  template_id: string;
  status: "pending" | "running" | "done" | "error";
  total_sent: number;
  total_failed: number;
  scheduled_for?: string;
  created_at: string;
}

export interface ProviderData {
  provider: "fonnte" | "waofficial" | "mimo" | string;
  quota_limit: number;
  quota_used: number;
  quota_remaining: number;
  reset_date: string;
}

export interface CampaignCost {
  campaign_id: string;
  cost_per_message: number;
  total_cost: number;
  currency: string;
}

export interface BlastTemplate {
  id: string;
  name: string;
  content: string;
  category_id: string | null;
}

export interface FollowUpTemplate {
  id: string;
  name: string;
  content: string;
  category_id: string | null;
}