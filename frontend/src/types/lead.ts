// Lead types
export type LeadStatus =
  | "Scraped"
  | "Contacted"
  | "Replied"
  | "Closed/Lost"
  | "Closed/Client"
  | "Siap Blast"
  | "WA Terkirim"
  | "Laporan Dibuka"
  | "Mulai Membaca"
  | "Membaca Serius"
  | "Prospek Hangat"
  | "Prospek Panas"
  | "Follow Up"
  | "Proposal Dikirim"
  | "Deal"
  | "Klien Aktif"
  | "Selesai";

export const LEAD_STATUSES: LeadStatus[] = [
  "Scraped", "Siap Blast", "WA Terkirim", "Laporan Dibuka", "Mulai Membaca",
  "Membaca Serius", "Prospek Hangat", "Prospek Panas", "Follow Up",
  "Proposal Dikirim", "Deal", "Replied", "Closed/Lost", "Closed/Client", "Klien Aktif", "Selesai",
];

export const STATUS_COLORS: Record<LeadStatus, string> = {
  Scraped: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  Contacted: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  Replied: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  "Closed/Lost": "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  "Closed/Client": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  "Siap Blast": "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
  "WA Terkirim": "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  "Laporan Dibuka": "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  "Mulai Membaca": "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  "Membaca Serius": "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  "Prospek Hangat": "bg-lime-100 text-lime-700 dark:bg-lime-900/30 dark:text-lime-300",
  "Prospek Panas": "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
  "Follow Up": "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  "Proposal Dikirim": "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
  Deal: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  "Klien Aktif": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  Selesai: "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300",
};

export const STATUS_LABELS: Record<string, string> = {
  Scraped: "Baru Discrape",
  Contacted: "Sudah Dihubungi",
  "Contacted/Sent": "WA Terkirim",
  Replied: "Sudah Membalas",
  "Closed/Lost": "Tidak Tertarik",
  "Closed/Client": "Klien Aktif",
  Closed: "Ditutup",
  HOT_PROSPECT: "Prospek Panas",
  WARM_STAGNANT: "Prospek Hangat - Perlu Follow Up",
  REPORT_VIEWED: "Laporan Dibuka",
  "Active Client": "Klien Aktif",
  "Siap Blast": "Siap Blast",
  "WA Terkirim": "WA Terkirim",
  "Laporan Dibuka": "Laporan Dibuka",
  "Mulai Membaca": "Mulai Membaca",
  "Membaca Serius": "Membaca Serius",
  "Prospek Hangat": "Prospek Hangat",
  "Prospek Panas": "Prospek Panas",
  "Follow Up": "Follow Up",
  "Proposal Dikirim": "Proposal Dikirim",
  Deal: "Deal",
  "Klien Aktif": "Klien Aktif",
  Selesai: "Selesai",
};

export function getLeadStatusLabel(status?: string | null): string {
  if (!status) return "Belum Ada Status";
  return STATUS_LABELS[status] || status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

export interface Lead {
  id: number;
  business_name: string;
  phone_number: string;
  address: string | null;
  original_url: string | null;
  status: LeadStatus;
  status_label?: string | null;
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
  score_adjustment?: number;
  score_adjustment_reason?: string | null;
  score_updated_at?: string | null;
}

export type LeadMap = Record<number, Lead>;

export interface SelectedService {
  id: string;
  name: string;
  price: number;
  features: string;
}
