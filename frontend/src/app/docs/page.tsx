"use client";

import { useState } from "react";
import { Book, ChevronRight, GitBranch, Check, Search } from "lucide-react";
import { SECTIONS, CATEGORIES } from "../../components/docs/docsData";
import WorkflowMap from "../../components/docs/WorkflowMap";

export default function DocsPage() {
  const [view, setView] = useState<"docs" | "workflow">("docs");
  const [search, setSearch] = useState("");
  const [activeId, setActiveId] = useState<string>(SECTIONS[0].id);

  const filtered = SECTIONS.filter(s => {
    if (!search) return true;
    const q = search.toLowerCase();
    return s.title.toLowerCase().includes(q) ||
      s.content.apa.toLowerCase().includes(q) ||
      s.content.fitur.some(f => f.toLowerCase().includes(q));
  });

  const active = SECTIONS.find(s => s.id === activeId) || SECTIONS[0];

  return (
    <div className="max-w-7xl mx-auto">
      {/* Tab toggle */}
      <div className="flex items-center gap-2 mb-5">
        <button
          onClick={() => setView("docs")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
            view === "docs"
              ? "bg-brand-yellow/10 text-brand-yellow border border-brand-yellow/30"
              : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
          }`}
        >
          <Book size={14} />
          Dokumentasi
        </button>
        <button
          onClick={() => setView("workflow")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
            view === "workflow"
              ? "bg-brand-yellow/10 text-brand-yellow border border-brand-yellow/30"
              : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
          }`}
        >
          <GitBranch size={14} />
          Alur Kerja
        </button>
      </div>

      {view === "workflow" ? (
        <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-6 sm:p-8 overflow-y-auto h-[calc(100vh-180px)]">
          <WorkflowMap />
        </div>
      ) : (
        <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-180px)]">
          {/* Sidebar */}
          <aside className="lg:w-72 shrink-0 flex flex-col gap-4">
            <div>
              <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-50">Dokumentasi</h1>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">Panduan lengkap setiap modul</p>
            </div>

            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
              <input
                id="docs-search"
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Cari modul..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-yellow/50"
              />
            </div>

            <nav className="flex-1 overflow-y-auto -mx-2">
              {CATEGORIES.map(cat => {
                const items = filtered.filter(s => s.category === cat);
                if (items.length === 0) return null;
                return (
                  <div key={cat} className="mb-3">
                    <p className="px-3 mb-1 text-[10px] font-bold uppercase tracking-widest text-neutral-400/70 dark:text-neutral-600">
                      {cat}
                    </p>
                    {items.map(s => (
                      <button
                        key={s.id}
                        onClick={() => setActiveId(s.id)}
                        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-colors text-left ${
                          activeId === s.id
                            ? "bg-brand-yellow/10 text-brand-yellow font-semibold"
                            : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                        }`}
                      >
                        {s.icon}
                        <span className="flex-1 truncate">{s.title}</span>
                        {activeId === s.id && <ChevronRight size={14} />}
                      </button>
                    ))}
                  </div>
                );
              })}
            </nav>
          </aside>

          {/* Content */}
          <main className="flex-1 overflow-y-auto bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-6 sm:p-8">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xs font-bold uppercase tracking-widest text-brand-yellow">
                {active.category}
              </span>
            </div>
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50 mb-4">{active.title}</h2>

            <section className="mb-6">
              <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 dark:text-neutral-400 mb-2">Apa ini?</h3>
              <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">{active.content.apa}</p>
            </section>

            <section className="mb-6">
              <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 dark:text-neutral-400 mb-3">Cara Kerja</h3>
              <ol className="space-y-2">
                {active.content.cara.map((step, i) => (
                  <li key={i} className="flex gap-3 text-sm text-neutral-700 dark:text-neutral-300">
                    <span className="shrink-0 w-6 h-6 rounded-full bg-brand-yellow/10 text-brand-yellow text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <span className="pt-0.5">{step}</span>
                  </li>
                ))}
              </ol>
            </section>

            <section className="mb-6">
              <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 dark:text-neutral-400 mb-3">Fitur Utama</h3>
              <ul className="grid sm:grid-cols-2 gap-2">
                {active.content.fitur.map((f, i) => (
                  <li key={i} className="flex gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                    <Check size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </section>

            {active.content.tips && (
              <section className="mb-6 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30 rounded-xl p-4">
                <h3 className="text-xs font-bold uppercase tracking-widest text-amber-700 dark:text-amber-400 mb-2">Tips & Catatan</h3>
                <ul className="space-y-1.5">
                  {active.content.tips.map((tip, i) => (
                    <li key={i} className="text-sm text-amber-900 dark:text-amber-200">• {tip}</li>
                  ))}
                </ul>
              </section>
            )}

            {active.content.faq && (
              <section className="mb-6">
                <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 dark:text-neutral-400 mb-3">Pertanyaan Umum</h3>
                <div className="space-y-3">
                  {active.content.faq.map((item, i) => (
                    <div key={i}>
                      <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">{item.q}</p>
                      <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{item.a}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
