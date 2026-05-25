"use client";

import { useState, useEffect, useCallback, FormEvent } from "react";
import { apiFetch } from "../../lib/api";
import Toast from "../../components/Toast";

interface Business {
  name: string;
  address: string;
  phone: string | null;
  whatsapp_url: string | null;
  google_rating: number | null;
  review_count: number | null;
  website_url: string | null;
}

interface CategoryOption {
  id: string;
  name: string;
}

interface ScrapeHistoryItem {
  id: number;
  category: string;
  location: string;
  product_interest: string | null;
  results_count: number;
  scraped_at: string;
}

export default function ScraperPage() {
  const [category, setCategory] = useState("");
  const [location, setLocation] = useState("");
  const [maxResults, setMaxResults] = useState(20);
  const [productInterest, setProductInterest] = useState("");
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Business[]>([]);
  const [history, setHistory] = useState<ScrapeHistoryItem[]>([]);
  const [historySearch, setHistorySearch] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await apiFetch("/api/categories?active_only=true");
      if (res.ok) {
        const data = await res.json();
        setCategories(data);
        if (data.length > 0 && !productInterest) setProductInterest(data[0].name);
      }
    } catch { /* silent */ }
  }, [productInterest]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await apiFetch("/api/scrape-history");
      if (res.ok) setHistory(await res.json());
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchCategories(); fetchHistory(); }, [fetchCategories, fetchHistory]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = `${category.trim()} ${location.trim()}`.trim();
    if (!q) return;
    setLoading(true);
    setResults([]);
    try {
      const params = new URLSearchParams({
        q, max_results: String(maxResults),
        product_interest: productInterest,
        category: category.trim(),
        location: location.trim(),
      });
      const res = await apiFetch(`/api/search?${params}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      const data: Business[] = await res.json();
      setResults(data);
      setToast({ message: `${data.length} bisnis ditemukan dan disimpan ke database.`, type: "success" });
      fetchHistory();
      if (aiAnalysis && data.length > 0) {
        runBatchAnalysis();
      }
    } catch (err: unknown) {
      setToast({ message: err instanceof Error ? err.message : "Terjadi kesalahan.", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  async function runBatchAnalysis() {
    setAnalyzing(true);
    try {
      const now = new Date();
      const day = String(now.getDate()).padStart(2, "0");
      const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
      const mon = months[now.getMonth()];
      const year = now.getFullYear();
      const batchName = `${category.trim()} - ${location.trim()} · ${day} ${mon} ${year}`;
      const res = await apiFetch(`/api/leads/analyze-batch?batch_name=${encodeURIComponent(batchName)}`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "running") {
          localStorage.setItem("analyze_batch", batchName);
          window.dispatchEvent(new StorageEvent("storage", { key: "analyze_batch", newValue: batchName }));
          setToast({ message: `Analisa dimulai untuk ${data.total} leads...`, type: "success" });
          pollAnalysisStatus(batchName);
        } else {
          setToast({ message: data.message, type: "success" });
          setAnalyzing(false);
        }
      } else {
        const body = await res.json().catch(() => ({}));
        setToast({ message: body.detail || "Gagal menganalisa.", type: "error" });
        setAnalyzing(false);
      }
    } catch {
      setToast({ message: "Gagal menjalankan AI Analysis.", type: "error" });
      setAnalyzing(false);
    }
  }

  function pollAnalysisStatus(batchName: string) {
    const interval = setInterval(async () => {
      try {
        const res = await apiFetch(`/api/leads/analyze-status?batch_name=${encodeURIComponent(batchName)}`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "done" || data.status === "idle") {
            clearInterval(interval);
            setAnalyzing(false);
          }
        }
      } catch { /* silent */ }
    }, 3000);
  }

  // Resume polling if there's an ongoing analysis
  useEffect(() => {
    const pending = localStorage.getItem("analyze_batch");
    if (pending) {
      setAnalyzing(true);
      pollAnalysisStatus(pending);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-4xl space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />

      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-[#fcfaf7]">Maps Scraper</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Cari bisnis lokal via Google Places dan simpan ke database.</p>
      </div>

      <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-sm p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Kategori Bisnis</label>
              <input type="text" placeholder='Contoh: "Biro Iklan", "Salon Kecantikan"'
                value={category} onChange={(e) => setCategory(e.target.value)} disabled={loading}
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 focus:border-amber-400 disabled:opacity-60 transition" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Lokasi</label>
              <input type="text" placeholder='Contoh: "Jakarta Selatan", "Surabaya"'
                value={location} onChange={(e) => setLocation(e.target.value)} disabled={loading}
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 focus:border-amber-400 disabled:opacity-60 transition" />
            </div>
          </div>

          <div className="flex items-end gap-4 flex-wrap">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Target Layanan</label>
              <select value={productInterest} onChange={(e) => setProductInterest(e.target.value)} disabled={loading}
                className="px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-60 transition">
                {categories.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
                {categories.length === 0 && <option value="">— Belum ada kategori —</option>}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Maks. Hasil</label>
              <select value={maxResults} onChange={(e) => setMaxResults(Number(e.target.value))} disabled={loading}
                className="px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-60 transition">
                {[10, 20, 40, 60].map((n) => <option key={n} value={n}>{n} hasil</option>)}
              </select>
            </div>
            <label className="flex items-center gap-2 cursor-pointer pb-1">
              <input type="checkbox" checked={aiAnalysis} onChange={(e) => setAiAnalysis(e.target.checked)} disabled={loading}
                className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
              <span className="text-xs text-gray-700 dark:text-gray-300 font-medium">AI Analysis</span>
              {analyzing && (
                <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl">
                  <div className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm font-medium text-amber-600 dark:text-amber-400">Menganalisa leads dengan AI... (proses tetap berjalan meski pindah halaman)</span>
                </div>
              )}
            </label>
            <button type="submit" disabled={loading || (!category.trim() && !location.trim())}
              className="flex items-center gap-2 px-6 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md">
              {loading ? (
                <><svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>Mencari...</>
              ) : (
                <><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>Mulai Scrape</>
              )}
            </button>
          </div>
        </form>
      </div>

      {loading && (
        <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-4 px-6 py-4 border-b border-[var(--border-subtle)] last:border-0 animate-pulse">
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/3" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6 ml-auto" />
            </div>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && category.trim() && (
        <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-sm p-8 text-center">
          <div className="text-4xl mb-3">🔍</div>
          <p className="text-sm font-semibold text-gray-700 dark:text-[#fcfaf7]">0 bisnis ditemukan</p>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1.5 max-w-md mx-auto">
            Tidak ada hasil untuk &quot;{category.trim()}{location.trim() ? ` ${location.trim()}` : ""}&quot;. Coba kata kunci lain atau perluas lokasi pencarian.
          </p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-700 dark:text-[#fcfaf7]">{results.length} bisnis ditemukan</p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-amber-600 font-medium bg-amber-50 px-2.5 py-1 rounded-full">{productInterest}</span>
              <span className="text-xs text-emerald-600 font-medium bg-emerald-50 px-2.5 py-1 rounded-full">Tersimpan ke DB</span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-[#2a2a29] border-b border-[var(--border-default)]">
                <tr>{["#", "Nama Bisnis", "Rating", "Alamat", "Nomor", "Website", "WhatsApp"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {results.map((biz, i) => (
                  <tr key={i} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                    <td className="px-4 py-3 text-gray-400 text-xs">{i + 1}</td>
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-[#fcfaf7]">{biz.name}</td>
                    <td className="px-4 py-3">
                      {biz.google_rating != null ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="text-amber-400"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                          <span className="text-amber-600 dark:text-amber-400">{biz.google_rating.toFixed(1)}</span>
                          {biz.review_count != null && <span className="text-gray-400">({biz.review_count})</span>}
                        </span>
                      ) : <span className="text-gray-300 text-xs">—</span>}
                    </td>
                    <td className="px-4 py-3 text-neutral-500 dark:text-neutral-400 text-xs max-w-[200px] leading-relaxed">{biz.address}</td>
                    <td className="px-4 py-3 font-mono text-gray-600 dark:text-gray-400 text-xs">{biz.phone ?? "—"}</td>
                    <td className="px-4 py-3">
                      {biz.website_url ? (
                        <a href={biz.website_url} target="_blank" rel="noopener noreferrer"
                          className="text-xs text-blue-500 hover:underline max-w-[120px] truncate block">
                          {biz.website_url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                        </a>
                      ) : <span className="text-gray-300 text-xs">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      {biz.whatsapp_url ? (
                        <a href={biz.whatsapp_url} target="_blank" rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-xs font-semibold rounded-lg transition-colors">
                          Chat WA
                        </a>
                      ) : <span className="text-gray-300 text-xs">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Riwayat Pencarian */}
      {history.length > 0 && (
        <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-gray-700 dark:text-[#fcfaf7]">Riwayat Pencarian</p>
              <p className="text-xs text-gray-400 mt-0.5">Kombinasi bisnis + lokasi yang sudah pernah di-scrape.</p>
            </div>
            <input type="text" value={historySearch} onChange={(e) => setHistorySearch(e.target.value)}
              placeholder="Cari lokasi atau kategori..."
              className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:outline-none focus:ring-2 focus:ring-amber-300 transition w-56" />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-[#2a2a29] border-b border-[var(--border-default)]">
                <tr>{["Tanggal", "Kategori Bisnis", "Lokasi", "Target Layanan", "Hasil"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {history.filter(h => {
                  if (!historySearch) return true;
                  const q = historySearch.toLowerCase();
                  return h.category.toLowerCase().includes(q) || h.location.toLowerCase().includes(q);
                }).map((h) => (
                  <tr key={h.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                    <td className="px-4 py-3 text-xs text-gray-500">{new Date(h.scraped_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}</td>
                    <td className="px-4 py-3 font-medium text-neutral-800 dark:text-neutral-200">{h.category}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{h.location || "—"}</td>
                    <td className="px-4 py-3"><span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">{h.product_interest || "—"}</span></td>
                    <td className="px-4 py-3 text-xs font-semibold text-emerald-600">{h.results_count} bisnis</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
