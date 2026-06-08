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
// Legacy DB color names (yellow/green/blue) are kept as aliases to neutral keys for backward compat
export const COLUMN_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  gray: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-600 dark:text-neutral-300" },
  neutral: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-600 dark:text-neutral-300" },
  stone: { bg: "bg-stone-50 dark:bg-stone-900/40", border: "border-stone-200 dark:border-stone-700", text: "text-stone-600 dark:text-stone-300" },
  slate: { bg: "bg-slate-50 dark:bg-slate-900/40", border: "border-slate-200 dark:border-slate-700", text: "text-slate-600 dark:text-slate-300" },
  warm: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-600 dark:text-neutral-300" },
  red: { bg: "bg-red-50/60 dark:bg-red-950/30", border: "border-red-200 dark:border-red-800", text: "text-red-600 dark:text-red-400" },
  orange: { bg: "bg-orange-50/60 dark:bg-orange-950/30", border: "border-orange-200 dark:border-orange-800", text: "text-orange-600 dark:text-orange-400" },
  cool: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", border: "border-neutral-300 dark:border-neutral-600", text: "text-neutral-600 dark:text-neutral-300" },
  accent: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", border: "border-neutral-300 dark:border-neutral-600", text: "text-neutral-600 dark:text-neutral-300" },
  purple: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", border: "border-neutral-300 dark:border-neutral-600", text: "text-neutral-600 dark:text-neutral-300" },
  pink: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", border: "border-neutral-300 dark:border-neutral-600", text: "text-neutral-600 dark:text-neutral-300" },
  // Legacy aliases (backward compat with existing DB data)
  yellow: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-600 dark:text-neutral-300" },
  green: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", border: "border-neutral-300 dark:border-neutral-600", text: "text-neutral-600 dark:text-neutral-300" },
  blue: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", border: "border-neutral-300 dark:border-neutral-600", text: "text-neutral-600 dark:text-neutral-300" },
};

export const BOARD_TOP_BORDER: Record<string, string> = {
  gray: "border-t-4 border-neutral-300 dark:border-neutral-600",
  neutral: "border-t-4 border-neutral-300 dark:border-neutral-600",
  stone: "border-t-4 border-stone-300 dark:border-stone-600",
  slate: "border-t-4 border-slate-400",
  warm: "border-t-4 border-neutral-300 dark:border-neutral-600",
  red: "border-t-4 border-red-400",
  orange: "border-t-4 border-orange-400",
  cool: "border-t-4 border-neutral-300 dark:border-neutral-600",
  accent: "border-t-4 border-neutral-300 dark:border-neutral-600",
  purple: "border-t-4 border-neutral-300 dark:border-neutral-600",
  pink: "border-t-4 border-neutral-300 dark:border-neutral-600",
  // Legacy aliases
  yellow: "border-t-4 border-neutral-300 dark:border-neutral-600",
  green: "border-t-4 border-neutral-300 dark:border-neutral-600",
  blue: "border-t-4 border-neutral-300 dark:border-neutral-600",
};

export const CARD_COLORS: Record<string, { bg: string; accent: string; text: string }> = {
  gray: { bg: "bg-neutral-50 dark:bg-neutral-900/30", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  neutral: { bg: "bg-neutral-50 dark:bg-neutral-900/30", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  stone: { bg: "bg-stone-50 dark:bg-stone-900/30", accent: "", text: "text-stone-600 dark:text-stone-300" },
  slate: { bg: "bg-slate-50 dark:bg-slate-900/30", accent: "", text: "text-slate-600 dark:text-slate-300" },
  warm: { bg: "bg-neutral-50 dark:bg-neutral-900/30", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  red: { bg: "bg-red-50/60 dark:bg-red-950/30", accent: "", text: "text-red-600 dark:text-red-400" },
  orange: { bg: "bg-orange-50/60 dark:bg-orange-950/30", accent: "", text: "text-orange-600 dark:text-orange-400" },
  cool: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  accent: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  purple: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  pink: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  // Legacy aliases
  yellow: { bg: "bg-neutral-50 dark:bg-neutral-900/30", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  green: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
  blue: { bg: "bg-neutral-100/60 dark:bg-neutral-800/40", accent: "", text: "text-neutral-600 dark:text-neutral-300" },
};

export const LABEL_COLORS: Record<string, string> = {
  gray: "bg-neutral-500", neutral: "bg-neutral-500", stone: "bg-stone-500",
  slate: "bg-slate-500",
  red: "bg-red-500", orange: "bg-orange-500",
  warm: "bg-neutral-500",
  cool: "bg-neutral-500", accent: "bg-neutral-500",
  purple: "bg-neutral-500", pink: "bg-neutral-500",
  // Legacy aliases
  yellow: "bg-neutral-500",
  green: "bg-neutral-500", blue: "bg-neutral-500",
};