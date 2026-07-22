"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Sun, Moon, Menu, Bell, Search } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  created_at: string;
  action_url?: string | null;
  is_read?: boolean;
}

export default function TopBar({
  onMenuClick,
  hideMenu,
  onSearchClick,
}: {
  onMenuClick?: () => void;
  hideMenu?: boolean;
  onSearchClick?: () => void;
}) {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    apiFetch("/api/notifications?limit=5")
      .then(r => r.ok ? r.json() : [])
      .then(data => setNotifications(Array.isArray(data) ? data : []))
      .catch(() => setNotifications([]));
  }, []);

  async function markNotificationRead(id: string) {
    await apiFetch(`/api/notifications/${id}/read`, { method: "POST" }).catch(() => null);
    setNotifications(prev => prev.filter(n => n.id !== id));
  }

  function formatNotificationTime(value: string) {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  const name = user?.name ?? "Admin";
  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <header className="h-14 shrink-0 bg-[var(--bg-surface)] border-b border-[var(--border-subtle)] flex items-center px-4 sm:px-6 justify-between">
      <div className="flex items-center gap-3 min-w-0">
        {!hideMenu && (
          <button onClick={onMenuClick} className="lg:hidden p-2 -ml-2 rounded-xl hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all" aria-label="Open menu">
            <Menu size={20} className="text-neutral-600 dark:text-neutral-300" />
          </button>
        )}
        <p className="text-sm font-semibold text-neutral-700 dark:text-neutral-200 truncate">
          Halo, {name}!
        </p>
      </div>
      <div className="flex items-center gap-1.5">
        {onSearchClick && (
          <button
            type="button"
            onClick={onSearchClick}
            className="flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-2.5 py-1.5 text-xs text-neutral-500 hover:bg-neutral-100 dark:border-neutral-700 dark:bg-neutral-800/60 dark:text-neutral-300 dark:hover:bg-neutral-800"
            aria-label="Global search"
            title="Cari (⌘K / Ctrl+K)"
          >
            <Search size={14} />
            <span className="hidden sm:inline">Cari…</span>
            <kbd className="hidden md:inline rounded border border-neutral-200 bg-white px-1 py-0.5 text-[10px] text-neutral-400 dark:border-neutral-600 dark:bg-neutral-900">⌘K</kbd>
          </button>
        )}
        <div className="relative">
          <button
            onClick={() => setNotificationsOpen(v => !v)}
            className="relative p-2 rounded-xl hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all duration-200"
            aria-label="Notifikasi"
            aria-expanded={notificationsOpen}
          >
            <Bell size={18} className={unreadCount > 0 ? "text-brand-yellow" : "text-neutral-500 dark:text-neutral-300"} />
            {unreadCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-yellow px-1 text-[9px] font-bold text-white">
                {unreadCount}
              </span>
            )}
          </button>
          {notificationsOpen && (
            <div className="absolute right-0 top-11 z-50 w-80 max-w-[calc(100vw-2rem)] rounded-xl border border-[var(--border-subtle)] bg-white p-2 shadow-xl dark:bg-neutral-900">
              <div className="flex items-center justify-between px-2 pb-2">
                <p className="text-xs font-bold text-neutral-700 dark:text-neutral-200">Notifikasi</p>
                <span className="text-[11px] text-neutral-400">{unreadCount} baru</span>
              </div>
              {notifications.length === 0 ? (
                <div className="px-2 py-4 text-xs text-neutral-400">Tidak ada notifikasi baru.</div>
              ) : (
                <div className="max-h-80 space-y-1 overflow-y-auto">
                  {notifications.map(n => {
                    const content = (
                      <>
                        <div className="text-xs font-semibold text-neutral-800 dark:text-neutral-100">{n.title}</div>
                        <div className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-neutral-500 dark:text-neutral-400">{n.message}</div>
                        <div className="mt-1 text-[10px] text-neutral-400">{formatNotificationTime(n.created_at)}</div>
                      </>
                    );
                    return (
                      <div key={n.id} className="rounded-lg px-2 py-2 hover:bg-neutral-50 dark:hover:bg-neutral-800">
                        {n.action_url ? (
                          <a href={n.action_url} className="block" onClick={() => setNotificationsOpen(false)}>
                            {content}
                          </a>
                        ) : content}
                        <div className="mt-2 flex justify-end">
                          <button onClick={() => markNotificationRead(n.id)} className="text-[11px] font-semibold text-brand-yellow">
                            Tandai dibaca
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
        {mounted && (
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-2 rounded-xl hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all duration-200"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun size={18} className="text-brand-yellow" />
            ) : (
              <Moon size={18} className="text-neutral-500" />
            )}
          </button>
        )}
      </div>
    </header>
  );
}
