"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../../lib/api";
import { Search, Copy, Trash2, ArrowUpDown } from "lucide-react";
import Toast from "../../components/Toast";
import Modal from "../../components/Modal";
import Pagination from "../../components/Pagination";

interface ProposalRecord {
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

function formatRupiah(num: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(num);
}

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<ProposalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const [analyticsMap, setAnalyticsMap] = useState<Record<string, { total_opens: number; total_time_seconds: number; last_opened: string | null }>>({});
  const [page, setPage] = useState(1);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const PAGE_SIZE = 20;

  const fetchProposals = useCallback(async () => {
    try {
      const res = await apiFetch("/api/proposals");
      if (res.ok) setProposals(await res.json());
    } finally { setLoading(false); }
  }, []);

  const fetchAnalytics = useCallback(async () => {
    try {
      const res = await apiFetch("/api/proposals/analytics/all");
      if (res.ok) {
        const data = await res.json();
        const map: Record<string, { total_opens: number; total_time_seconds: number; last_opened: string | null }> = {};
        for (const item of data) {
          map[item.proposal_id] = { total_opens: item.total_opens, total_time_seconds: item.total_time_seconds, last_opened: item.last_opened };
        }
        setAnalyticsMap(map);
      }
    } catch { /* silent */ }
  }, []);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchProposals(); fetchAnalytics();
    intervalRef.current = setInterval(() => { fetchProposals(); fetchAnalytics(); }, 30000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchProposals, fetchAnalytics]);

  const filteredProposals = proposals
    .filter((p) =>
      !search || (p.business_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
      p.services_detail.some((s) => s.name.toLowerCase().includes(search.toLowerCase()))
    )
    .sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return sortOrder === "desc" ? dateB - dateA : dateA - dateB;
    });

  function copyLink(proposal: ProposalRecord) {
    const link = `${window.location.origin}/proposal/${proposal.id}`;
    navigator.clipboard.writeText(link);
    setToast({ message: "Link proposal tersalin!", type: "info" });
  }

  async function deleteProposal(id: string) {
    const res = await apiFetch(`/api/proposals/${id}`, { method: "DELETE" });
    if (res.ok) {
      setProposals(prev => prev.filter(p => p.id !== id));
      setToast({ message: "Proposal berhasil dihapus.", type: "success" });
    } else {
      setToast({ message: "Gagal hapus proposal.", type: "error" });
    }
    setDeleteId(null);
  }

  return (
    <div className="max-w-6xl space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={!!deleteId}
        title="Hapus Proposal?"
        message="Proposal yang dihapus tidak bisa dikembalikan. Yakin ingin melanjutkan?"
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteId && deleteProposal(deleteId)}
        onCancel={() => setDeleteId(null)}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Riwayat Proposal</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Semua proposal yang pernah dibuat untuk klien.</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Cari klien atau layanan..."
              className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition" />
          </div>
        </div>

        {loading ? (
          <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="flex gap-4 px-6 py-4 border-b border-[var(--border-subtle)] last:border-0 animate-pulse">
                <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/5" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" />
                <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6 ml-auto" />
              </div>
            ))}
          </div>
        ) : filteredProposals.length === 0 ? (
          <div className="text-center py-12 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
            {search ? "Tidak ada proposal yang cocok." : "Belum ada proposal. Buat proposal dari halaman Buku Klien."}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl shadow-sm border border-[var(--border-default)]">
            <table className="w-full bg-[var(--bg-surface)] text-sm">
              <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-[var(--border-default)]">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide whitespace-nowrap cursor-pointer select-none" onClick={() => setSortOrder(prev => prev === "desc" ? "asc" : "desc")}>
                    <span className="inline-flex items-center gap-1">Tanggal <ArrowUpDown size={12} className="opacity-60" /></span>
                  </th>
                  {["Klien", "Layanan", "Harga", "Status", "Statistik", "Aksi"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {filteredProposals.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((p) => (
                  <tr key={p.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                    <td className="px-4 py-3 text-xs text-gray-500">{p.created_at ? new Date(p.created_at).toLocaleDateString("id-ID") : "—"}</td>
                    <td className="px-4 py-3 font-semibold text-neutral-800 dark:text-neutral-200">{p.business_name ?? "—"}</td>
                    <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400">{p.services_detail.map((s) => s.name).join(", ")}</td>
                    <td className="px-4 py-3 text-xs font-semibold text-brand-yellow">{formatRupiah(p.total_price)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${p.status === "Accepted" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : p.status === "Rejected" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {(() => {
                        const stats = analyticsMap[p.id];
                        if (!stats || stats.total_opens === 0) return <span className="text-xs text-gray-300 dark:text-gray-600">Belum dibuka</span>;
                        const isHot = stats.total_time_seconds > 60;
                        return (
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-600 dark:text-gray-400">{stats.total_opens}x dibuka</span>
                            </div>
                            <p className="text-[10px] text-gray-400">{Math.floor(stats.total_time_seconds / 60)}m {stats.total_time_seconds % 60}s baca</p>
                            {isHot && <span className="inline-block px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-[9px] font-bold rounded uppercase">Hot Lead</span>}
                          </div>
                        );
                      })()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <p className="text-[11px] text-neutral-500 dark:text-neutral-400 font-mono truncate max-w-[200px]">
                          {p.slug ? `/p/${p.slug}` : `/proposal/${p.id.slice(0, 8)}...`}
                        </p>
                        <div className="flex items-center gap-2">
                          <button onClick={() => copyLink(p)} className="inline-flex items-center gap-1 text-xs text-brand-yellow hover:underline font-medium">
                            <Copy size={11} /> Copy Link
                          </button>
                          <button onClick={() => setDeleteId(p.id)} className="inline-flex items-center gap-1 text-xs text-red-400 hover:text-red-600 font-medium">
                            <Trash2 size={11} /> Hapus
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} pageSize={PAGE_SIZE} total={filteredProposals.length} onPageChange={setPage} itemLabel="proposal" />
            <div className="px-4 py-2 bg-neutral-50 dark:bg-neutral-800 border-t border-[var(--border-default)] text-xs text-gray-400">
              {filteredProposals.length} proposal
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
