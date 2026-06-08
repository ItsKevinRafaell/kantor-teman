"use client";

import { useState } from "react";
import { apiFetch } from "../../lib/api";
import { copyToClipboard } from "./types";
import type { ContentGeneration } from "./types";

interface Props {
  sessionId: string | null;
  sharedContext: string[];
  showToast: (m: string, t?: "success" | "error" | "info") => void;
  onResult: (g: ContentGeneration) => void;
}

export default function CaptionPanel({ sessionId, sharedContext, showToast, onResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [tone, setTone] = useState("casual");
  const [keywords, setKeywords] = useState("");
  const [result, setResult] = useState<{ caption: string; hashtags: string[]; notes: string } | null>(null);

  async function generate() {
    if (!topic.trim()) return;
    setLoading(true); setResult(null);
    try {
      const res = await apiFetch("/api/content/generate/caption", {
        method: "POST",
        body: JSON.stringify({
          topic, platform, tone,
          keywords: keywords ? keywords.split(",").map(k => k.trim()).filter(Boolean) : [],
          session_id: sessionId,
          context_from: sharedContext,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult({ caption: data.caption || "", hashtags: data.hashtags || [], notes: data.notes || "" });
        onResult({
          id: data.id, session_id: sessionId || undefined, tool_type: "caption",
          input_data: { topic, platform, tone }, output_data: data, status: "done", created_at: data.created_at,
        });
        showToast("Caption berhasil dibuat!");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal generate caption", "error");
      }
    } catch {
      showToast("Gagal generate caption", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
      <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-200">Caption Sosial Media</h2>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Topik / Deskripsi *</label>
        <textarea value={topic} onChange={e => setTopic(e.target.value)} rows={3}
          placeholder="Contoh: Promo diskon 50% untuk jasa pembuatan website UMKM..."
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm resize-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Platform</label>
          <select value={platform} onChange={e => setPlatform(e.target.value)}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none">
            <option value="instagram">Instagram</option>
            <option value="tiktok">TikTok</option>
            <option value="facebook">Facebook</option>
            <option value="linkedin">LinkedIn</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Tone</label>
          <select value={tone} onChange={e => setTone(e.target.value)}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none">
            {["casual", "profesional", "fun", "edukatif", "persuasif"].map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Keywords (pisahkan koma)</label>
        <input type="text" value={keywords} onChange={e => setKeywords(e.target.value)}
          placeholder="website, UMKM, diskon"
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none" />
      </div>
      <button onClick={generate} disabled={loading || !topic.trim()}
        className="w-full py-2.5 bg-neutral-500 hover:bg-neutral-600 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition-all flex items-center justify-center gap-2">
        {loading
          ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Generating...</>
          : "Generate Caption"}
      </button>
      {result && (
        <div className="space-y-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
            <p className="text-sm text-neutral-800 dark:text-neutral-200 whitespace-pre-wrap">{result.caption}</p>
          </div>
          {result.hashtags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.hashtags.map((tag, i) => (
                <span key={i} className="px-2 py-0.5 bg-neutral-100 dark:bg-neutral-800/30 text-neutral-700 dark:text-neutral-300 text-xs rounded-full">{tag}</span>
              ))}
            </div>
          )}
          {result.notes && <p className="text-xs text-neutral-400 italic">{result.notes}</p>}
          <div className="flex gap-2">
            <button onClick={() => copyToClipboard(`${result.caption}\n\n${result.hashtags.join(" ")}`)}
              className="flex-1 py-2 text-xs rounded-lg bg-gray-100 dark:bg-gray-800 text-neutral-600 hover:bg-gray-200 dark:hover:bg-gray-700">Copy Caption + Hashtags</button>
            <button onClick={() => copyToClipboard(result.caption)}
              className="flex-1 py-2 text-xs rounded-lg bg-neutral-50 dark:bg-neutral-800/20 text-neutral-700 hover:bg-neutral-100">Copy Caption Only</button>
          </div>
        </div>
      )}
    </div>
  );
}
