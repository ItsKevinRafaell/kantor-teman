"use client";

import { useApi } from "../lib/swr";
import type { Analytics, Patterns, BoardOverview, FinanceOverview } from "../types";

export interface HotLead {
  lead_id: number;
  business_name: string;
  phone_number: string;
  category: string | null;
  status: string;
  last_active: string;
  total_opens: number;
  proposal_slug: string | null;
}

export interface TopScoredLead {
  id: number;
  business_name: string;
  phone_number: string;
  lead_score: number;
  status: string;
  product_interest: string | null;
  address: string | null;
}

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

interface UseDashboardDataReturn {
  analytics: Analytics | undefined;
  patterns: Patterns | undefined;
  hotLeads: HotLead[];
  topScoredLeads: TopScoredLead[];
  alerts: ReengagementAlert[];
  boardOverview: BoardOverview[];
  financeOverview: FinanceOverview | undefined;
  isLoading: boolean;
}

export function useDashboardData(): UseDashboardDataReturn {
  const { data: analytics } = useApi<Analytics>("/api/analytics");
  const { data: patterns } = useApi<Patterns>("/api/analytics/patterns");
  const { data: hotLeads = [] } = useApi<HotLead[]>("/api/leads/hot");
  const { data: topScoredLeads = [] } = useApi<TopScoredLead[]>("/api/leads/top-scored?limit=10");
  const { data: alerts = [] } = useApi<ReengagementAlert[]>("/api/alerts/reengagement");
  const { data: boardOverview = [] } = useApi<BoardOverview[]>("/api/boards/overview");
  const { data: financeOverview } = useApi<FinanceOverview>("/api/finance/reports");

  const isLoading = !analytics && !hotLeads;

  return {
    analytics,
    patterns,
    hotLeads,
    topScoredLeads,
    alerts,
    boardOverview,
    financeOverview,
    isLoading,
  };
}