"use client";

import { useState } from "react";
import { apiFetch } from "../../lib/api";
import { copyToClipboard, markdownToHtml, exportToDocx } from "./types";
import { publishArticleToCms } from "./cmsUtils";
import type { ContentGeneration, ContentGenResult } from "./types";

const SERP_OPTIONS = [
  { value: "featured_snippet", label: "Featured Snippet" },
  { value: "paa", label: "People Also Ask" },
  { value: "local_pack", label: "Local Pack" },
  { value: "image_pack", label: "Image Pack" },
];

interface Props {
  sessionId: string | null;
  sharedContext: string[];
  showToast: (m: string, t?: "success" | "error" | "info") => void;
  onResult: (g: ContentGeneration) => void;
}

export default function SeoArticlePanel({ sessionId, sharedContext, showToast, onResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [title, setTitle] = useState("");
  const [wordCount, setWordCount] = useState(800);
  const [tone, setTone] = useState("informatif");
  const [searchIntent, setSearchIntent] = useState("informational");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [keywordDifficulty, setKeywordDifficulty] = useState("");
  const [searchVolume, setSearchVolume] = useState("");
  const [lsiKeywords, setLsiKeywords] = useState("");
  const [faqTopics, setFaqTopics] = useState("");
  const [serpFeatures, setSerpFeatures] = useState<string[]>([]);
  const [targetAudience, setTargetAudience] = useState("");
  const [targetLocation, setTargetLocation] = useState("");
  const [brandName, setBrandName] = useState("");
  const [uniqueAngle, setUniqueAngle] = useState("");
  const [internalLinkTargets, setInternalLinkTargets] = useState("");
  const [result, setResult] = useState<ContentGenResult | null>(null);

  function toggleSerp(val: string) {
    setSerpFeatures(prev => prev.includes(val) ? prev.filter(v => v !== val) : [...prev, val]);
  }

  async function generate() {
    if (!keyword.trim()) return;
    setLoading(true); setResult(null);
    try {
      const res = await apiFetch("/api/content/generate/seo-article", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          keyword, title: title || undefined, word_count: wordCount, tone,
          search_intent: searchIntent,
          keyword_difficulty: keywordDifficulty ? parseInt(keywordDifficulty) : undefined,
          search_volume: searchVolume ? parseInt(searchVolume) : undefined,
          lsi_keywords: lsiKeywords ? lsiKeywords.split(",").map(k => k.trim()).filter(Boolean) : [],
          faq_topics: faqTopics ? faqTopics.split("\n").map(q => q.trim()).filter(Boolean) : [],
          serp_features: serpFeatures,
          target_audience: targetAudience || undefined,
          target_location: targetLocation || undefined,
          brand_name: brandName || undefined,
          unique_angle: uniqueAngle || undefined,
          internal_link_targets: internalLinkTargets || undefined,
          session_id: sessionId,
          context_from: sharedContext,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
        onResult({ id: data.id, session_id: sessionId || undefined, tool_type: "seo_article",
          input_data: { keyword, word_count: wordCount }, output_data: data, status: "done", created_at: data.created_at });
        showToast("Artikel berhasil dibuat!");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal generate artikel", "error");
      }
    } catch {
      showToast("Gagal generate artikel", "error");
    } finally {
      setLoading(false);
    }
  }

  async function handleExportDocx() {
    if (!result) return;
    setExporting(true);
    try {
      await exportToDocx(result);
      showToast("DOCX berhasil diexport!");
    } catch {
      showToast("Gagal export DOCX", "error");
    } finally {
      setExporting(false);
    }
  }

  async function handlePublishToCms() {
    if (!result) return;
    setPublishing(true);
    try {
      await publishArticleToCms(result);
      showToast("Artikel terkirim ke CMS sebagai draft!");
    } catch (e: unknown) {
      showToast(`Gagal kirim ke CMS: ${e instanceof Error ? e.message : "Error tidak diketahui"}`, "error");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="space-y-4 rounded-2xl border border-amber-100 bg-white p-5 shadow-sm dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
      <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-200">Penulis Artikel SEO</h2>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Keyword Utama *</label>
          <input type="text" value={keyword} onChange={e => setKeyword(e.target.value)}
            placeholder="jasa pembuatan website murah"
            className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Judul (opsional)</label>
          <input type="text" value={title} onChange={e => setTitle(e.target.value)}
            placeholder="Otomatis dari keyword"
            className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Search Intent</label>
          <select value={searchIntent} onChange={e => setSearchIntent(e.target.value)}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none">
            <option value="informational">Informational — edukasi</option>
            <option value="commercial">Commercial — pertimbangan</option>
            <option value="transactional">Transactional — konversi</option>
            <option value="navigational">Navigational — brand</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Tone</label>
          <select value={tone} onChange={e => setTone(e.target.value)}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none">
            {["informatif", "persuasif", "edukatif", "casual"].map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Jumlah Kata: {wordCount}</label>
        <input type="range" min={400} max={2000} step={200} value={wordCount} onChange={e => setWordCount(Number(e.target.value))}
          className="w-full accent-amber-500" />
        <div className="flex justify-between text-xs text-neutral-400 mt-1"><span>400</span><span>2000</span></div>
      </div>

      <button onClick={() => setShowAdvanced(p => !p)}
        className="flex w-full items-center gap-2 rounded-lg border border-amber-100 px-3 py-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-amber-50 dark:border-amber-900/40 dark:text-neutral-300 dark:hover:bg-amber-950/20">
        <span className="text-xs">{showAdvanced ? "▾" : "▸"}</span>
        <span>{showAdvanced ? "Sembunyikan data lanjutan" : "Data Semrush & konteks lanjutan (opsional)"}</span>
        {!showAdvanced && <span className="ml-auto text-xs text-neutral-400">KD · Volume · LSI · FAQ · dll</span>}
      </button>

      {showAdvanced && (
        <div className="space-y-4 rounded-xl border border-amber-100 bg-amber-50/30 p-4 dark:border-amber-900/40 dark:bg-amber-950/10">
          <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest">Data Semrush</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Search Volume <span className="font-normal normal-case text-neutral-300">/bulan</span></label>
              <input type="number" value={searchVolume} onChange={e => setSearchVolume(e.target.value)}
                placeholder="1200"
                className="w-full px-3 py-2 bg-white dark:bg-neutral-800/70 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Keyword Difficulty <span className="font-normal normal-case text-neutral-300">0-100</span></label>
              <input type="number" min={0} max={100} value={keywordDifficulty} onChange={e => setKeywordDifficulty(e.target.value)}
                placeholder="45"
                className="w-full px-3 py-2 bg-white dark:bg-neutral-800/70 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">LSI / Related Keywords <span className="font-normal normal-case text-neutral-300">pisah koma</span></label>
            <input type="text" value={lsiKeywords} onChange={e => setLsiKeywords(e.target.value)}
              placeholder="jasa web murah, buat website toko online, harga website profesional"
              className="w-full px-3 py-2 bg-white dark:bg-neutral-800/70 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Target SERP Features</label>
            <div className="flex flex-wrap gap-2">
              {SERP_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => toggleSerp(opt.value)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all border
                    ${serpFeatures.includes(opt.value)
                      ? "bg-amber-500 text-white border-amber-500"
                      : "bg-white dark:bg-neutral-800/70 text-neutral-500 border-gray-200 dark:border-gray-700 hover:border-amber-300"}`}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">FAQ Topics <span className="font-normal normal-case text-neutral-300">1 pertanyaan per baris</span></label>
            <textarea value={faqTopics} onChange={e => setFaqTopics(e.target.value)} rows={3}
              placeholder={"Berapa biaya membuat website?\nBerapa lama proses pembuatan?\nApakah bisa request desain custom?"}
              className="w-full px-3 py-2 bg-white dark:bg-neutral-800/70 border border-gray-200 dark:border-gray-700 rounded-lg text-sm resize-none focus:ring-2 focus:ring-amber-300 outline-none" />
          </div>
          <hr className="border-gray-200 dark:border-gray-700" />
          <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest">Konteks Bisnis</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Target Pembaca</label>
              <input type="text" value={targetAudience} onChange={e => setTargetAudience(e.target.value)}
                placeholder="UMKM, pemilik toko online"
                className="w-full px-3 py-2 bg-white dark:bg-neutral-800/70 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Target Lokasi</label>
              <input type="text" value={targetLocation} onChange={e => setTargetLocation(e.target.value)}
                placeholder="Jakarta, Indonesia"
                className="w-full px-3 py-2 bg-white dark:bg-neutral-800/70 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Nama Brand</label>
              <input type="text" value={brandName} onChange={e => setBrandName(e.target.value)}
                placeholder="Teman UMKM Kita"
                className="w-full px-3 py-2 bg-white dark:bg-neutral-800/70 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Internal Link Targets</label>
              <input type="text" value={internalLinkTargets} onChange={e => setInternalLinkTargets(e.target.value)}
                placeholder="/blog/tips-umkm, /layanan/website"
                className="w-full px-3 py-2 bg-white dark:bg-neutral-800/70 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Angle Unik Artikel</label>
            <input type="text" value={uniqueAngle} onChange={e => setUniqueAngle(e.target.value)}
              placeholder="Fokus pada UMKM kuliner, dengan contoh nyata, bukan teori"
              className="w-full px-3 py-2 bg-white dark:bg-neutral-800/70 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 outline-none" />
          </div>
        </div>
      )}

      {sharedContext.length > 0 && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/10 dark:text-amber-300">
          {sharedContext.length} konteks dari history akan digunakan
        </p>
      )}

      <button onClick={generate} disabled={loading || !keyword.trim()}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-amber-500 py-2.5 text-sm font-semibold text-white transition-all hover:bg-amber-600 disabled:opacity-50">
        {loading
          ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Sedang menulis artikel...</>
          : "Generate Artikel"}
      </button>

      {result && (
        <div className="space-y-3 pt-2 border-t border-gray-100 dark:border-gray-700">
          <div className="rounded-xl bg-amber-50/60 p-3 dark:bg-amber-950/10">
            <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-400 mb-1">Meta Description</p>
            <p className="text-sm text-neutral-700 dark:text-neutral-300">{result.meta_description}</p>
          </div>
          {result.secondary_keywords?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              <span className="text-xs text-neutral-400 self-center">Secondary keywords:</span>
              {result.secondary_keywords.map((k, i) => (
                <span key={i} className="px-2 py-0.5 bg-neutral-100 dark:bg-neutral-800/30 text-neutral-700 dark:text-neutral-300 text-xs rounded-full">{k}</span>
              ))}
            </div>
          )}
          <div className="max-h-96 overflow-y-auto rounded-xl bg-white p-4 ring-1 ring-amber-100 dark:bg-neutral-800/60 dark:ring-amber-900/30">
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mb-3 text-base">{result.title}</h3>
            <div className="prose-content" dangerouslySetInnerHTML={{ __html: markdownToHtml(result.body) }} />
          </div>
          <div className="flex gap-2 flex-wrap">
            <button onClick={() => copyToClipboard(`# ${result.title}\n\n${result.body}`)}
              className="flex-1 py-2 text-xs rounded-lg bg-gray-100 dark:bg-neutral-800/70 text-neutral-600 hover:bg-gray-200 dark:hover:bg-gray-700">Copy Markdown</button>
            <button onClick={() => copyToClipboard(result.meta_description)}
              className="flex-1 py-2 text-xs rounded-lg bg-neutral-50 dark:bg-neutral-800/20 text-neutral-700 hover:bg-neutral-100">Copy Meta</button>
            <button onClick={handleExportDocx} disabled={exporting}
              className="flex-1 py-2 text-xs rounded-lg bg-neutral-50 dark:bg-neutral-800/20 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 disabled:opacity-50 flex items-center justify-center gap-1">
              {exporting ? <><div className="w-3 h-3 border-2 border-neutral-500 border-t-transparent rounded-full animate-spin" />Exporting...</> : "Export DOCX"}
            </button>
            <button onClick={handlePublishToCms} disabled={publishing}
              className="flex-1 py-2 text-xs rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 disabled:opacity-50 flex items-center justify-center gap-1">
              {publishing ? <><div className="w-3 h-3 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />Mengirim...</> : "Kirim ke CMS"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
