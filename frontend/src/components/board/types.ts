export interface Lead { id: number; business_name: string; }

export interface BoardUser {
  id: number;
  name: string;
  email?: string;
  role?: string;
}

export interface BoardCard {
  id: string; column_id: string; title: string; description: string | null;
  assignee: string | null; due_date: string | null; labels: string[];
  position: number; is_archived: boolean; created_at: string; updated_at: string | null;
  lead_id?: number | null; lead?: Lead | null; color?: string;
  is_workspace_linked?: boolean;
  comments: { id: string; content: string; author: string; created_at: string }[];
  checklist: { id: string; text: string; is_done: boolean; position?: number; created_at?: string }[];
  activity: { id: string; action: string; description: string; actor: string; created_at: string }[];
  attachments: { id: string; card_id: string; file_path: string; file_name: string; file_type?: string | null; uploaded_by?: string | null; uploaded_at: string }[];
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
  yellow: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  gray: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  neutral: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  stone: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  slate: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  warm: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  red: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  orange: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  cool: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  accent: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  purple: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  pink: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  green: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  blue: { bg: "bg-neutral-50 dark:bg-neutral-900/40", border: "border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
};

export const BOARD_TOP_BORDER: Record<string, string> = {
  yellow: "border-t-2 border-neutral-200 dark:border-neutral-700",
  gray: "border-t-2 border-neutral-200 dark:border-neutral-700",
  neutral: "border-t-2 border-neutral-200 dark:border-neutral-700",
  stone: "border-t-2 border-neutral-200 dark:border-neutral-700",
  slate: "border-t-2 border-neutral-200 dark:border-neutral-700",
  warm: "border-t-2 border-neutral-200 dark:border-neutral-700",
  red: "border-t-2 border-neutral-200 dark:border-neutral-700",
  orange: "border-t-2 border-neutral-200 dark:border-neutral-700",
  cool: "border-t-2 border-neutral-200 dark:border-neutral-700",
  accent: "border-t-2 border-neutral-200 dark:border-neutral-700",
  purple: "border-t-2 border-neutral-200 dark:border-neutral-700",
  pink: "border-t-2 border-neutral-200 dark:border-neutral-700",
  green: "border-t-2 border-neutral-200 dark:border-neutral-700",
  blue: "border-t-2 border-neutral-200 dark:border-neutral-700",
};

export const CARD_COLORS: Record<string, { bg: string; accent: string; text: string }> = {
  yellow: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  gray: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  neutral: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  stone: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  slate: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  warm: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  red: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  orange: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  cool: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  accent: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  purple: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  pink: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  green: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
  blue: { bg: "bg-white dark:bg-neutral-900/50", accent: "border border-neutral-200 dark:border-neutral-700", text: "text-neutral-700 dark:text-neutral-300" },
};

export const LABEL_COLORS: Record<string, string> = {
  yellow: "bg-amber-300",
  gray: "bg-neutral-300", neutral: "bg-neutral-300", stone: "bg-stone-300",
  slate: "bg-slate-300",
  red: "bg-rose-300", orange: "bg-orange-300",
  warm: "bg-amber-300",
  cool: "bg-sky-300", accent: "bg-teal-300",
  purple: "bg-violet-300", pink: "bg-pink-300",
  green: "bg-emerald-300", blue: "bg-sky-300",
};
