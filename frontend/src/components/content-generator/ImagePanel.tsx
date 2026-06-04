"use client";

import { useState } from "react";
import { apiFetch } from "../../lib/api";
import { copyToClipboard } from "./types";
import type { ContentProvider, ContentGeneration } from "./types";

interface Props {
  sessionId: string | null;
  sharedContext: string[];
  providers: ContentProvider[];
  showToast: (m: string, t?: "success" | "error" | "info") => void;
  onResult: (g: ContentGeneration) => void;
}

export default function ImagePanel({ sessionId, sharedContext, providers, showToast, onResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [providerId, setProviderId] = useState(providers[0]?.id ?? "");
  const [size, setSize] = useState("512x512");
  const [images, setImages] = useState<{ type: string; value: string; id?: string }[]>([]);

  const [w, h] = size.split("x").map(Number);

  async function generate() {
    if (!prompt.trim() || !providerId) return;
    setLoading(true); setImages([]);
    try {
      const res = await apiFetch("/api/content/generate/image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt, provider_id: providerId, session_id: sessionId,
          negative_prompt: negativePrompt || undefined, width: w, height: h,
          context_from: sharedContext,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setImages((data.images || []).map((img: { type: string; value: string }) => ({ ...img, id: data.id })));
        onResult({
          id: data.id, session_id: sessionId || undefined, tool_type: "image",
          input_data: { prompt, provider_id: providerId, size },
          output_data: data, status: "done", created_at: data.created_at,
        });
        showToast("Gambar berhasil dibuat!");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal generate image", "error");
      }
    } catch {
      showToast("Gagal generate image", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
      <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-200">Image Generator</h2>

      {providers.length === 0 ? (
        <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-4 text-center">
          <p className="text-sm text-amber-700 dark:text-amber-400">Belum ada image provider.</p>
          <p className="text-xs text-neutral-400 mt-1">Klik "Kelola Image Provider" di sidebar untuk menambahkan.</p>
        </div>
      ) : (
        <>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Provider</label>
            <select value={providerId} onChange={e => setProviderId(e.target.value)}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none">
              {providers.map(p => <option key={p.id} value={p.id}>{p.name} ({p.model})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Prompt *</label>
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={3}
              placeholder="Describe the image you want to generate..."
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm resize-none focus:ring-2 focus:ring-yellow-400 outline-none" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Negative Prompt</label>
              <input type="text" value={negativePrompt} onChange={e => setNegativePrompt(e.target.value)}
                placeholder="blurry, low quality..."
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Ukuran</label>
              <select value={size} onChange={e => setSize(e.target.value)}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none">
                {["512x512", "768x768", "1024x1024", "1024x576", "576x1024"].map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          <button onClick={generate} disabled={loading || !prompt.trim() || !providerId}
            className="w-full py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition-all flex items-center justify-center gap-2">
            {loading
              ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Generating...</>
              : "Generate Image"}
          </button>

          {images.length > 0 && (
            <div className="space-y-3 pt-2 border-t border-gray-100 dark:border-gray-700">
              <div className="grid grid-cols-2 gap-3">
                {images.map((img, i) => (
                  <div key={i} className="relative group rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700">
                    <img src={img.type === "b64" ? `data:image/png;base64,${img.value}` : img.value}
                      alt={`Generated ${i + 1}`} className="w-full h-48 object-cover" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <a href={img.type === "b64" ? `data:image/png;base64,${img.value}` : img.value}
                        download={`generated-${i + 1}.png`}
                        className="px-3 py-1.5 bg-white text-neutral-800 text-xs rounded-lg font-medium">Download</a>
                      {img.type === "url" && (
                        <button onClick={() => copyToClipboard(img.value)}
                          className="px-3 py-1.5 bg-white text-neutral-800 text-xs rounded-lg font-medium">Copy URL</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
