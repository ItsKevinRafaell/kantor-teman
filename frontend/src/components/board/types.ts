export interface Lead { id: number; business_name: string; }

export interface BoardCard {
  id: string; column_id: string; title: string; description: string | null;
  assignee: string | null; due_date: string | null; labels: string[];
  position: number; is_archived: boolean; created_at: string; updated_at: string | null;
  lead_id?: number | null; lead?: Lead | null; color?: string;
  is_workspace_linked?: boolean;
  comments: { id: string; content: string; author: string; created_at: string }[];
  checklist: { id: string; text: string; is_done: boolean }[];
  activity: { id: string; action: string; description: string; actor: string; created_at: string }[];
}

export interface BoardColumn {
  id: string; board_id: string; name: string; position: number; color?: string; cards: BoardCard[];
}

export interface Board {
  id: string; project_id: string; created_at: string; color?: string; columns: BoardColumn[];
}

export interface BoardOverview {
  project_id: string; project_name: string; board_id: string;
  cards_count: number; columns_count: number; client_name?: string;
  overdue_cards?: string[]; due_soon_cards?: string[];
  color?: string; project_lead_id?: number | null; is_archived?: boolean;
}

export interface Project {
  id: string; name: string; type: string; status: string; lead_id: number | null; color?: string; is_archived?: boolean; nominal?: number;
}

// Calm neutral palette — status recognizability via subtle border + text, not bright fills
export const COLUMN_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  yellow: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-600 dark:text-neutral-300" },
  red: { bg: "bg-red-50/60 dark:bg-red-950/30", border: "border-red-200 dark:border-red-800", text: "text-red-600 dark:text-red-400" },
  orange: { bg: "bg-orange-50/60 dark:bg-orange-950/30", border: "border-orange-200 dark:border-orange-800", text: "text-orange-600 dark:text-orange-400" },
  green: { bg: "bg-emerald-50/60 dark:bg-emerald-950/30", border: "border-emerald-200 dark:border-emerald-800", text: "text-emerald-600 dark:text-emerald-400" },
  blue: { bg: "bg-blue-50/60 dark:bg-blue-950/30", border: "border-blue-200 dark:border-blue-800", text: "text-blue-600 dark:text-blue-400" },
  purple: { bg: "bg-violet-50/60 dark:bg-violet-950/30", border: "border-violet-200 dark:border-violet-800", text: "text-violet-600 dark:text-violet-400" },
  pink: { bg: "bg-pink-50/60 dark:bg-pink-950/30", border: "border-pink-200 dark:border-pink-800", text: "text-pink-600 dark:text-pink-400" },
  slate: { bg: "bg-slate-50 dark:bg-slate-900/40", border: "border-slate-200 dark:border-slate-700", text: "text-slate-600 dark:text-slate-300" },
};

export const BOARD_TOP_BORDER: Record<string, string> = {
  yellow: "border-t-4 border-neutral-300 dark:border-neutral-600",
  red: "border-t-4 border-red-400",
  orange: "border-t-4 border-orange-400",
  green: "border-t-4 border-emerald-400",
  blue: "border-t-4 border-blue-400",
  purple: "border-t-4 border-violet-400",
  pink: "border-t-4 border-pink-400",
  slate: "border-t-4 border-slate-400",
};

export const CARD_COLORS: Record<string, { bg: string; accent: string; text: string }> = {
  yellow: { bg: "bg-neutral-50 dark:bg-neutral-900/30", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  red: { bg: "bg-red-50/60 dark:bg-red-950/30", accent: "", text: "text-red-600 dark:text-red-400" },
  orange: { bg: "bg-orange-50/60 dark:bg-orange-950/30", accent: "", text: "text-orange-600 dark:text-orange-400" },
  green: { bg: "bg-emerald-50/60 dark:bg-emerald-950/30", accent: "", text: "text-emerald-600 dark:text-emerald-400" },
  blue: { bg: "bg-blue-50/60 dark:bg-blue-950/30", accent: "", text: "text-blue-600 dark:text-blue-400" },
  purple: { bg: "bg-violet-50/60 dark:bg-violet-950/30", accent: "", text: "text-violet-600 dark:text-violet-400" },
  pink: { bg: "bg-pink-50/60 dark:bg-pink-950/30", accent: "", text: "text-pink-600 dark:text-pink-400" },
  slate: { bg: "bg-slate-50 dark:bg-slate-900/30", accent: "", text: "text-slate-600 dark:text-slate-300" },
};

export const LABEL_COLORS: Record<string, string> = {
  red: "bg-red-500", orange: "bg-orange-500", yellow: "bg-amber-500",
  green: "bg-green-500", blue: "bg-blue-500", purple: "bg-purple-500", pink: "bg-pink-500",
};