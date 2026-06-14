"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "../contexts/AuthContext";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const STATIC_LOGO = "/logo-secondary.png";
const STATIC_API_LOGO = `${API_BASE}/uploads/brand/logo-secondary.png`;

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: "MENU UTAMA",
    items: [
      {
        href: "/dashboard",
        label: "Dashboard",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></svg>,
      },
      {
        href: "/docs",
        label: "Panduan",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>,
      },
    ],
  },
  {
    title: "KLIEN DAN PROYEK",
    items: [
      {
        href: "/clients",
        label: "Klien",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>,
      },
      {
        href: "/board",
        label: "Board Proyek",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="5" height="18" rx="1" /><rect x="10" y="3" width="5" height="12" rx="1" /><rect x="17" y="3" width="5" height="15" rx="1" /></svg>,
      },
      {
        href: "/workspace",
        label: "Workspace Klien",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>,
      },
    ],
  },
  {
    title: "OPERASI",
    items: [
      {
        href: "/leads",
        label: "Prospek",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>,
      },
      {
        href: "/proposals",
        label: "Proposal",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>,
      },
      {
        href: "/finance",
        label: "Keuangan",
        adminOnly: true,
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2" /><path d="M12 8v8" /><path d="M8 12h8" /></svg>,
      },
    ],
  },
  {
    title: "MARKETING",
    items: [
      {
        href: "/marketing/campaigns",
        label: "Campaign & Kuota",
        adminOnly: true,
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2" /><path d="M16 3l-4 4-4-4" /></svg>,
      },
      {
        href: "/marketing/blast-analytics",
        label: "Analitik Pesan",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
      },
      {
        href: "/marketing/calendar",
        label: "Kalender Konten",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>,
      },
      {
        href: "/content-generator",
        label: "Generator Konten",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>,
      },
    ],
  },
  {
    title: "DOKUMEN & LAPORAN",
    items: [
      {
        href: "/master/internal-vault",
        label: "Arsip Internal",
        adminOnly: true,
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /><circle cx="12" cy="16" r="1" /></svg>,
      },
      {
        href: "/documents",
        label: "Dokumen & Laporan",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /></svg>,
      },
      {
        href: "/documents/generator",
        label: "Dokumen Resmi",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="9" y1="14" x2="15" y2="14" /><line x1="9" y1="18" x2="15" y2="18" /></svg>,
      },
      {
        href: "/documents/reports",
        label: "Laporan Klien",
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18" /><path d="M7 15l3-3 3 2 5-7" /><path d="M18 7h-4" /><path d="M18 7v4" /></svg>,
      },
    ],
  },
  {
    title: "PENGATURAN",
    items: [
      {
        href: "/master/products",
        label: "Katalog Produk",
        adminOnly: true,
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>,
      },
      {
        href: "/master/categories",
        label: "Kategori Produk",
        adminOnly: true,
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h6v6H4z" /><path d="M14 4h6v6h-6z" /><path d="M4 14h6v6H4z" /><path d="M14 14h6v6h-6z" /></svg>,
      },
      {
        href: "/master/templates",
        label: "Template Teks",
        adminOnly: true,
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16v2H4z" /><path d="M4 10h10v2H4z" /><path d="M4 16h6v2H4z" /></svg>,
      },
      {
        href: "/master/brand-kit",
        label: "Brand Kit",
        adminOnly: true,
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" /></svg>,
      },
      {
        href: "/tasks",
        label: "Antrean Tugas",
        adminOnly: true,
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>,
      },
      {
        href: "/settings",
        label: "Pengaturan",
        adminOnly: true,
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>,
      },
    ],
  },
];

export default function Sidebar({ open, onClose }: { open?: boolean; onClose?: () => void }) {
  const pathname = usePathname();
  const { isAdmin } = useAuth();
  const [customizing, setCustomizing] = useState(false);
  const [hiddenItems, setHiddenItems] = useState<Set<string>>(new Set());
  const [logoUrl, setLogoUrl] = useState<string>(STATIC_LOGO);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("sidebar_hidden_items");
      if (stored) setHiddenItems(new Set(JSON.parse(stored)));
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/api/brand-kit/public`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data?.assets) return;
        const logo = data.assets.find((a: { asset_type: string; file_url?: string }) => a.asset_type === "logo_secondary");
        const nextLogo = logo?.file_url ? `${API_BASE}${logo.file_url}` : STATIC_API_LOGO;
        setLogoUrl(nextLogo);
      })
      .catch(() => setLogoUrl(STATIC_API_LOGO));
  }, []);

  function toggleItem(href: string) {
    setHiddenItems(prev => {
      const next = new Set(prev);
      if (next.has(href)) next.delete(href);
      else next.add(href);
      localStorage.setItem("sidebar_hidden_items", JSON.stringify(Array.from(next)));
      return next;
    });
  }

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={onClose} />
      )}
      <aside className={`fixed lg:static inset-y-0 left-0 z-50 w-60 shrink-0 bg-[var(--bg-surface)] dark:bg-[var(--bg-surface)] border-r border-[var(--border-subtle)] flex flex-col h-full transform transition-transform duration-200 ease-in-out ${open ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0`}>
        <div className="px-6 py-5 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <div>
            <img src={logoUrl} alt="Teman UMKM Kita" className="h-8 w-auto object-contain" onError={() => setLogoUrl(STATIC_LOGO)} />
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-0.5 font-medium uppercase tracking-widest">CRM Internal</p>
          </div>
          <div className="relative flex items-center gap-1">
            <button onClick={onClose} className="lg:hidden p-1 text-neutral-400 hover:text-neutral-600">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
          {NAV_GROUPS.map((group) => {
            const visibleItems = group.items
              .filter(i => isAdmin || !i.adminOnly)
              .filter(i => customizing || !hiddenItems.has(i.href));
            if (visibleItems.length === 0 && !customizing) return null;
            return (
            <div key={group.title}>
              <p className="px-3 mb-2 text-[10px] font-bold uppercase tracking-widest text-neutral-400/70 dark:text-neutral-600">
                {group.title}
              </p>
              <div className="space-y-0.5">
                {visibleItems.map((item) => {
                  const active = pathname === item.href || pathname === item.href + "/" || (item.href !== "/dashboard" && pathname.startsWith(item.href) && !NAV_GROUPS.some(g => g.items.some(i => i.href !== item.href && i.href.startsWith(item.href) && pathname.startsWith(i.href))));
                  const isHidden = hiddenItems.has(item.href);
                  if (customizing) {
                    return (
                      <button key={item.href} onClick={() => toggleItem(item.href)}
                        className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium transition-all ${isHidden ? "opacity-40 line-through" : ""} text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100/80 dark:hover:bg-neutral-800/60`}>
                        <input type="checkbox" checked={!isHidden} readOnly className="w-3.5 h-3.5 rounded border-gray-300 text-brand-yellow pointer-events-none" />
                        <span className="text-neutral-400 dark:text-neutral-500">{item.icon}</span>
                        <span className="truncate">{item.label}</span>
                      </button>
                    );
                  }
                  return (
                    <Link key={item.href} href={item.href} onClick={onClose}
                      className={`flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-200 group ${active ? "bg-brand-yellow/10 text-brand-yellow shadow-sm" : "text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100/80 dark:hover:bg-neutral-800/60 hover:text-neutral-800 dark:hover:text-neutral-200"}`}>
                      <span className={`transition-colors duration-200 ${active ? "text-brand-yellow" : "text-neutral-400 dark:text-neutral-500 group-hover:text-neutral-600 dark:group-hover:text-neutral-300"}`}>
                        {item.icon}
                      </span>
                      <span className="truncate">{item.label}</span>
                      {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-yellow animate-pulse" />}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
          })}
        </nav>

        <div className="px-3 py-3 border-t border-[var(--border-subtle)] flex items-center justify-between">
          <p className="text-[11px] text-neutral-400 dark:text-neutral-600 font-medium px-2">v1.0</p>
          <button onClick={() => setCustomizing(!customizing)}
            className={`text-[11px] font-medium px-2.5 py-1 rounded-lg transition-colors ${customizing ? "bg-brand-yellow text-white" : "text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}
            title="Pilih menu mana yang tampil di sidebar">
            {customizing ? "Selesai" : "Atur Menu"}
          </button>
        </div>
      </aside>
    </>
  );
}
