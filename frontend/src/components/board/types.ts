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

export const COLUMN_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  yellow: { bg: "bg-yellow-50 dark:bg-yellow-900/20", border: "border-yellow-300 dark:border-yellow-700", text: "text-yellow-700 dark:text-yellow-300" },
  red: { bg: "bg-red-50 dark:bg-red-900/20", border: "border-red-300 dark:border-red-700", text: "text-red-700 dark:text-red-300" },
  orange: { bg: "bg-orange-50 dark:bg-orange-900/20", border: "border-orange-300 dark:border-orange-700", text: "text-orange-700 dark:text-orange-300" },
  green: { bg: "bg-green-50 dark:bg-green-900/20", border: "border-green-300 dark:border-green-700", text: "text-green-700 dark:text-green-300" },
  blue: { bg: "bg-blue-50 dark:bg-blue-900/20", border: "border-blue-300 dark:border-blue-700", text: "text-blue-700 dark:text-blue-300" },
  purple: { bg: "bg-purple-50 dark:bg-purple-900/20", border: "border-purple-300 dark:border-purple-700", text: "text-purple-700 dark:text-purple-300" },
  pink: { bg: "bg-pink-50 dark:bg-pink-900/20", border: "border-pink-300 dark:border-pink-700", text: "text-pink-700 dark:text-pink-300" },
  slate: { bg: "bg-slate-50 dark:bg-slate-900/20", border: "border-slate-300 dark:border-slate-600", text: "text-slate-700 dark:text-slate-300" },
};

export const BOARD_TOP_BORDER: Record<string, string> = {
  yellow: "border-t-4 border-yellow-400",
  red: "border-t-4 border-red-400",
  orange: "border-t-4 border-orange-400",
  green: "border-t-4 border-green-400",
  blue: "border-t-4 border-blue-400",
  purple: "border-t-4 border-purple-400",
  pink: "border-t-4 border-pink-400",
  slate: "border-t-4 border-slate-400",
};

export const CARD_COLORS: Record<string, { bg: string; accent: string; text: string }> = {
  yellow: { bg: "bg-yellow-50 dark:bg-yellow-900/25", accent: "", text: "text-yellow-700 dark:text-yellow-300" },
  red: { bg: "bg-red-50 dark:bg-red-900/25", accent: "", text: "text-red-700 dark:text-red-300" },
  orange: { bg: "bg-orange-50 dark:bg-orange-900/25", accent: "", text: "text-orange-700 dark:text-orange-300" },
  green: { bg: "bg-green-50 dark:bg-green-900/25", accent: "", text: "text-green-700 dark:text-green-300" },
  blue: { bg: "bg-blue-50 dark:bg-blue-900/25", accent: "", text: "text-blue-700 dark:text-blue-300" },
  purple: { bg: "bg-purple-50 dark:bg-purple-900/25", accent: "", text: "text-purple-700 dark:text-purple-300" },
  pink: { bg: "bg-pink-50 dark:bg-pink-900/25", accent: "", text: "text-pink-700 dark:text-pink-300" },
  slate: { bg: "bg-slate-50 dark:bg-slate-900/25", accent: "", text: "text-slate-700 dark:text-slate-300" },
};

export const LABEL_COLORS: Record<string, string> = {
  red: "bg-red-500", orange: "bg-orange-500", yellow: "bg-amber-500",
  green: "bg-green-500", blue: "bg-blue-500", purple: "bg-purple-500", pink: "bg-pink-500",
};