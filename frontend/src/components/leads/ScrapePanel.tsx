"use client";

import { useState, useEffect, useCallback, FormEvent } from "react";
import { apiFetch } from "../../lib/api";
import Toast from "../Toast";
import { INDONESIA_LOCATION_PRESETS } from "../../lib/indonesiaLocations";

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
  batch_name: string | null;
  lead_count: number;
}

interface HistoryResponse {
  items: ScrapeHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

interface Props {
  onBatchSelect: (batchName: string) => void;
}

const LOCATION_PRESETS = INDONESIA_LOCATION_PRESETS;

export default function ScrapePanel({ onBatchSelect }: Props) {
  const [category, setCategory] = useState("");
  const [location, setLocation] = useState("");
  const [province, setProvince] = useState("DKI Jakarta");
  const [city, setCity] = useState("Jakarta Selatan");
  const [district, setDistrict] = useState("");
  const [manualLocation, setManualLocation] = useState("");
  const [citySearch, setCitySearch] = useState("");
  const [maxResults, setMaxResults] = useState(20);
  const [productInterest, setProductInterest] = useState("");
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Business[]>([]);
  const [history, setHistory] = useState<ScrapeHistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historySearch, setHistorySearch] = useState("");
  const [historySearchInput, setHistorySearchInput] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const PAGE_SIZE = 20;

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

  const fetchHistory = useCallback(async (page = 1, search = "", from = "", to = "") => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (search) params.set("search", search);
      if (from) params.set("date_from", from);
      if (to) params.set("date_to", to);
      const res = await apiFetch(`/api/scrape-history?${params}`);
      if (res.ok) {
        const data: HistoryResponse = await res.json();
        setHistory(data.items);
        setHistoryTotal(data.total);
        setHistoryPage(data.page);
      }
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchCategories(); fetchHistory(); }, [fetchCategories, fetchHistory]);

  useEffect(() => {
    const t = setTimeout(() => {
      setHistorySearch(historySearchInput);
      fetchHistory(1, historySearchInput, dateFrom, dateTo);
    }, 350);
    return () => clearTimeout(t);
  }, [historySearchInput, dateFrom, dateTo, fetchHistory]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const selectedLocation = buildLocation();
    const q = `${category.trim()} ${selectedLocation}`.trim();
    if (!q) return;
    setLoading(true);
    setResults([]);
    try {
      const params = new URLSearchParams({
        q, max_results: String(maxResults),
        product_interest: productInterest,
        category: category.trim(),
        location: selectedLocation,
      });
      const res = await apiFetch(`/api/search?${params}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      const data: Business[] = await res.json();
      setResults(data);
      setToast({ message: `${data.length} bisnis ditemukan dan disimpan ke database.`, type: "success" });
      fetchHistory(1, historySearch, dateFrom, dateTo);
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
      const batchName = `${category.trim()} - ${buildLocation()} · ${day} ${mon} ${year}`;
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

  function buildLocation() {
    const manual = manualLocation.trim();
    if (manual) return manual;
    return [district.trim(), city.trim(), province.trim()].filter(Boolean).join(", ");
  }

  const provinceNames = Object.keys(LOCATION_PRESETS);
  const filteredCities = (LOCATION_PRESETS[province] || []).filter(c =>
    !citySearch.trim() || c.toLowerCase().includes(citySearch.trim().toLowerCase())
  );

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

  useEffect(() => {
    const pending = localStorage.getItem("analyze_batch");
    if (pending) {
      setAnalyzing(true);
      pollAnalysisStatus(pending);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />

      <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-[var(--border-default)] shadow-sm p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Kategori Bisnis</label>
              <input type="text" placeholder='Contoh: "Biro Iklan", "Salon Kecantikan"'
                value={category} onChange={(e) => setCategory(e.target.value)} disabled={loading}
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 focus:border-amber-400 disabled:opacity-60 transition" />
            </div>
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Lokasi</label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <select value={province} onChange={(e) => { const next = e.target.value; setProvince(next); setCity(LOCATION_PRESETS[next]?.[0] || ""); setCitySearch(""); }} disabled={loading}
                  className="px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-60 transition">
                  {provinceNames.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <div className="space-y-1">
                  <input type="search" value={citySearch} onChange={(e) => setCitySearch(e.target.value)} placeholder="Cari kota/kab."
                    disabled={loading}
                    className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-60 transition" />
                  <select value={city} onChange={(e) => setCity(e.target.value)} disabled={loading}
                    className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-60 transition">
                    {filteredCities.map(c => <option key={c} value={c}>{c}</option>)}
                    {filteredCities.length === 0 && <option value={city}>{city || "Tidak ada kota cocok"}</option>}
                  </select>
                </div>
                <input type="text" placeholder="Kecamatan (opsional)"
                  value={district} onChange={(e) => setDistrict(e.target.value)} disabled={loading}
                  className="px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-60 transition" />
              </div>
              <input type="text" placeholder="Atau tulis lokasi bebas, mis. Canggu Bali"
                value={manualLocation} onChange={(e) => { setManualLocation(e.target.value); setLocation(e.target.value); }} disabled={loading}
                className="w-full px-4 py-2.5 border border-amber-100 dark:border-amber-900/50 rounded-xl text-sm bg-amber-50/40 dark:bg-amber-950/10 dark:text-neutral-50 focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-60 transition" />
              <p className="text-xs text-neutral-400">Preset mencakup seluruh provinsi Indonesia. Untuk kecamatan/desa spesifik, pakai kolom lokasi bebas.</p>
            </div>
          </div>

          <div className="flex items-end gap-4 flex-wrap">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Target Layanan</label>
              <select value={productInterest} onChange={(e) => setProductInterest(e.target.value)} disabled={loading}
                className="px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-60 transition">
                {categories.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
                {categories.length === 0 && <option value="">— Belum ada kategori —</option>}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Maks. Hasil</label>
              <select value={maxResults} onChange={(e) => setMaxResults(Number(e.target.value))} disabled={loading}
                className="px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-60 transition">
                {[10, 20, 40, 60].map((n) => <option key={n} value={n}>{n} hasil</option>)}
              </select>
            </div>
            <label className="flex items-center gap-2 cursor-pointer pb-1">
              <input type="checkbox" checked={aiAnalysis} onChange={(e) => setAiAnalysis(e.target.checked)} disabled={loading}
                className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
              <span className="text-xs text-gray-700 dark:text-gray-300 font-medium">Analisa AI setelah scrape</span>
              {analyzing && (
                <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl">
                  <div className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm font-medium text-amber-600 dark:text-amber-400">Menganalisa leads dengan AI...</span>
                </div>
              )}
            </label>
            <button type="submit" disabled={loading || (!category.trim() && !buildLocation())}
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
        <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-4 px-6 py-4 border-b border-[var(--border-subtle)] last:border-0 animate-pulse">
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/3" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6 ml-auto" />
            </div>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && category.trim() && (
        <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-[var(--border-default)] shadow-sm p-8 text-center">
          <div className="text-4xl mb-3 text-neutral-300"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div>
          <p className="text-sm font-semibold text-gray-700 dark:text-neutral-50">0 bisnis ditemukan</p>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1.5 max-w-md mx-auto">
            Tidak ada hasil untuk &quot;{category.trim()}{location.trim() ? ` ${location.trim()}` : ""}&quot;. Coba kata kunci lain atau perluas lokasi pencarian.
          </p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-700 dark:text-neutral-50">{results.length} bisnis ditemukan</p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-amber-600 font-medium bg-amber-50 px-2.5 py-1 rounded-full">{productInterest}</span>
              <span className="text-xs text-emerald-600 font-medium bg-emerald-50 px-2.5 py-1 rounded-full">Tersimpan ke DB</span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-[var(--bg-surface)] border-b border-[var(--border-default)]">
                <tr>{["#", "Nama Bisnis", "Rating", "Alamat", "Nomor", "Website", "WhatsApp"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {results.map((biz, i) => (
                  <tr key={i} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                    <td className="px-4 py-3 text-gray-400 text-xs">{i + 1}</td>
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-neutral-50">{biz.name}</td>
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

      <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
        <div className="px-6 py-4 border-b border-[var(--border-default)] flex items-center justify-between flex-wrap gap-3">
          <div>
            <p className="text-sm font-semibold text-gray-700 dark:text-neutral-50">Riwayat Batch Scraping</p>
            <p className="text-xs text-gray-400 mt-0.5">Klik batch untuk lihat di tab Tabel. Total: {historyTotal} batch.</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
              className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition"
              title="Dari tanggal" />
            <span className="text-xs text-neutral-400">→</span>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
              className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition"
              title="Sampai tanggal" />
            {(dateFrom || dateTo) && (
              <button onClick={() => { setDateFrom(""); setDateTo(""); }}
                className="text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-200 px-2 py-1">
                Clear
              </button>
            )}
            <input type="text" value={historySearchInput} onChange={(e) => setHistorySearchInput(e.target.value)}
              placeholder="Cari kategori, lokasi, atau batch..."
              className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition w-56" />
          </div>
        </div>
        {history.length === 0 ? (
          <div className="p-8 text-center text-xs text-neutral-400">
            {historySearch ? "Tidak ada batch yang cocok." : "Belum ada riwayat scraping."}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-[var(--bg-surface)] border-b border-[var(--border-default)]">
                  <tr>{["Tanggal", "Kategori Bisnis", "Lokasi", "Target Layanan", "Hasil", "Leads"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{h}</th>
                  ))}</tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {history.map((h) => (
                    <tr key={h.id}
                      onClick={() => onBatchSelect(h.batch_name || h.category)}
                      className="hover:bg-[var(--bg-surface-hover)] transition-colors cursor-pointer">
                      <td className="px-4 py-3 text-xs text-gray-500">{new Date(h.scraped_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}</td>
                      <td className="px-4 py-3 font-medium text-neutral-800 dark:text-neutral-200">{h.category}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{h.location || "—"}</td>
                      <td className="px-4 py-3"><span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">{h.product_interest || "—"}</span></td>
                      <td className="px-4 py-3 text-xs font-semibold text-emerald-600">{h.results_count} bisnis</td>
                      <td className="px-4 py-3 text-xs font-semibold text-blue-600">{h.lead_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {historyTotal > PAGE_SIZE && (
              <div className="px-6 py-3 border-t border-[var(--border-subtle)] flex items-center justify-between">
                <span className="text-xs text-neutral-400">
                  Halaman {historyPage} dari {Math.ceil(historyTotal / PAGE_SIZE)}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => fetchHistory(historyPage - 1, historySearch, dateFrom, dateTo)}
                    disabled={historyPage <= 1}
                    className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-neutral-800 transition"
                  >Prev</button>
                  <button
                    onClick={() => fetchHistory(historyPage + 1, historySearch, dateFrom, dateTo)}
                    disabled={historyPage >= Math.ceil(historyTotal / PAGE_SIZE)}
                    className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-neutral-800 transition"
                  >Next</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
