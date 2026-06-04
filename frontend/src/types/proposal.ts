// Proposal types
export interface TimelinePhase {
  sequence: number;
  title: string;
  description: string;
}

export interface ProposalRecord {
  id: string;
  lead_id: number;
  services_detail: { name: string; price: number; features: string[] }[];
  total_price: number;
  additional_options: string | null;
  status: string;
  created_at: string | null;
  business_name: string | null;
  phone_number: string | null;
  slug: string | null;
}

export interface ProposalAnalytics {
  proposal_id: string;
  total_opens: number;
  total_time_seconds: number;
  last_opened: string | null;
}

export interface ProposalSuccess {
  open: boolean;
  url: string;
}

export interface TimelineTemplate {
  id: string;
  name: string;
  timeline_data: TimelinePhase[];
}