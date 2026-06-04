"use client";

import { useState, useEffect } from "react";
import { Zap } from "lucide-react";
import { apiFetch } from "../../lib/api";
import { PIPELINE_STAGES, AI_FEATURES, type PipelineStage } from "./docsData";

interface AiProxy { id: string; name: string; model: string; feature: string | null; is_active: boolean; }

export default function WorkflowMap() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [proxies, setProxies] = useState<AiProxy[]>([]);
  const [proxiesLoading, setProxiesLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/ai-proxies")
      .then(r => r.ok ? r.json() : [])
      .then(data => setProxies(data))
      .catch(() => {})
      .finally(() => setProxiesLoading(false));
  }, []);

  const stage = PIPELINE_STAGES.find((s: PipelineStage) => s.id === expanded);

  return (
    <div className="space-y-10">
      {/* Business Pipeline */}
      <div>
        <div className="mb-4">
          <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-50">Pipeline Bisnis</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Klik tiap node untuk lihat alur lengkap, trigger, output, dan aksi
          </p>
        </div>
        <div className="overflow-x-auto pb-2">
          <div className="flex items-start gap-1 min-w-max px-1">
            {PIPELINE_STAGES.map((s: PipelineStage, i: number) => (
              <div key={s.id} className="flex items-start gap-1">
                <div className="flex flex-col items-center gap-2">
                  <button
                    onClick={() => setExpanded(expanded === s.id ? null : s.id)}
                    className={`relative flex flex-col items-center gap-1.5 px-3 py-3 rounded-2xl border-2 transition-all w-28 ${
                      expanded === s.id
                        ? `${s.bgClass} ${s.borderClass} shadow-lg scale-105`
                        : "bg-[var(--bg-surface)] border-[var(--border-default)] hover:shadow-md"
                    }`}
                  >
                    <s.Icon size={24} className={expanded === s.id ? s.colorClass : "text-neutral-500"} />
                    <span className={`text-xs font-bold ${expanded === s.id ? s.colorClass : "text-neutral-700 dark:text-neutral-300"}`}>{s.label}</span>
                    <span className="text-[10px] text-neutral-400 text-center leading-tight">{s.sub}</span>
                  </button>
                  {s.badge && (
                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${s.bgClass} ${s.colorClass} border ${s.borderClass} whitespace-nowrap`}>
                      <Zap size={8} className="inline -mt-0.5 mr-0.5" />{s.badge}
                    </span>
                  )}
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <div className="flex items-center mt-6 px-0.5">
                    <div className="w-5 h-0.5 bg-neutral-300 dark:bg-neutral-700" />
                    <div className="w-0 h-0 border-t-4 border-b-4 border-l-[6px] border-transparent border-l-neutral-300 dark:border-l-neutral-700" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {stage && (
          <div className={`mt-3 p-5 rounded-2xl border-2 ${stage.bgClass} ${stage.borderClass}`}>
            <div className="flex items-center gap-3 mb-4">
              <stage.Icon size={28} className={stage.colorClass} />
              <div>
                <h3 className={`font-bold text-base ${stage.colorClass}`}>{stage.label}</h3>
                <p className="text-xs text-neutral-500">{stage.sub}</p>
              </div>
              <a href={stage.link}
                className={`ml-auto text-xs font-semibold px-3 py-1.5 rounded-xl ${stage.bgClass} ${stage.colorClass} border ${stage.borderClass} hover:opacity-80 transition-opacity`}>
                Buka halaman →
              </a>
            </div>
            <div className="mb-4 p-4 rounded-xl bg-white/60 dark:bg-neutral-900/40 border border-[var(--border-subtle)]">
              <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">{stage.flow}</p>
              <p className="text-xs text-neutral-500 mt-2 font-medium">{stage.nextHint}</p>
            </div>
            <div className="grid sm:grid-cols-2 gap-4 text-sm">
              <div><p className="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1">Trigger</p><p className="text-neutral-700 dark:text-neutral-300">{stage.trigger}</p></div>
              <div><p className="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1">Output</p><p className="text-neutral-700 dark:text-neutral-300">{stage.output}</p></div>
              <div><p className="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1">Fitur AI</p><p className="text-neutral-700 dark:text-neutral-300">{stage.ai}</p></div>
              <div><p className="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1">Aksi Manual</p><p className="text-neutral-700 dark:text-neutral-300">{stage.manual}</p></div>
            </div>
          </div>
        )}
      </div>

      {/* AI System Map */}
      <div>
        <div className="mb-4">
          <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-50">Sistem AI</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Tiap fitur bisa pakai model berbeda — routing otomatis lewat per-feature proxy
          </p>
        </div>
        <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-2xl p-6">
          <div className="flex flex-wrap gap-3 justify-center mb-2">
            {AI_FEATURES.map(f => (
              <div key={f.feature} className="flex flex-col items-center gap-0.5 px-5 py-3 rounded-2xl bg-neutral-100 dark:bg-neutral-800 border border-[var(--border-default)]">
                <span className={`text-sm font-bold ${f.color}`}>{f.name}</span>
                <span className="text-[10px] text-neutral-400">{f.sub}</span>
                <span className="text-[9px] font-mono text-neutral-400 mt-0.5">feature="{f.feature}"</span>
              </div>
            ))}
          </div>
          <div className="flex justify-center">
            <div className="flex flex-col items-center">
              <div className="w-0.5 h-6 bg-neutral-300 dark:bg-neutral-700" />
              <div className="px-6 py-2.5 rounded-xl bg-brand-yellow/10 border-2 border-brand-yellow/40 text-center">
                <p className="text-xs font-bold text-brand-yellow font-mono">get_proxy_for_feature()</p>
                <p className="text-[10px] text-neutral-500 mt-0.5">feature-specific → fallback → default endpoint</p>
              </div>
              <div className="w-0.5 h-6 bg-neutral-300 dark:bg-neutral-700" />
            </div>
          </div>
          {proxiesLoading ? (
            <p className="text-center text-sm text-neutral-400 py-4">Memuat proxy...</p>
          ) : proxies.length === 0 ? (
            <p className="text-center text-sm text-neutral-400 py-4">Belum ada proxy. Tambah di Settings → AI Engine → AI Proxies.</p>
          ) : (
            <div className="flex flex-wrap gap-3 justify-center">
              {proxies.map(p => (
                <div key={p.id} className={`flex flex-col items-center gap-0.5 px-4 py-2.5 rounded-xl border border-[var(--border-default)] ${p.is_active ? "bg-emerald-500/10" : "bg-neutral-500/10"}`}>
                  <span className={`text-sm font-bold ${p.is_active ? "text-emerald-600 dark:text-emerald-400" : "text-neutral-500"}`}>{p.name}</span>
                  <span className="text-[10px] text-neutral-400">{p.model || "default"}</span>
                  {p.feature && <span className="text-[9px] font-mono text-neutral-400">{p.feature}</span>}
                </div>
              ))}
            </div>
          )}
          <p className="text-center text-[11px] text-neutral-400 mt-5">
            Tambah provider baru di <span className="font-semibold text-neutral-500 dark:text-neutral-300">Settings → AI Engine → AI Proxies</span>
          </p>
        </div>
      </div>
    </div>
  );
}
