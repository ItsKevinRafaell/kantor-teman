"use client";

import { useState } from "react";
import { useTheme } from "next-themes";
import { Sun, Moon, Menu } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

export default function TopBar({ onMenuClick, hideMenu }: { onMenuClick?: () => void; hideMenu?: boolean }) {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Handle mount for SSR theme
  useState(() => setMounted(true));

  const name = user?.name ?? "Admin";

  return (
    <header className="h-14 shrink-0 bg-[var(--bg-surface)] border-b border-[var(--border-subtle)] flex items-center px-4 sm:px-6 justify-between">
      <div className="flex items-center gap-3">
        {!hideMenu && (
          <button onClick={onMenuClick} className="lg:hidden p-2 -ml-2 rounded-xl hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all" aria-label="Open menu">
            <Menu size={20} className="text-neutral-600 dark:text-neutral-300" />
          </button>
        )}
        <p className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
          Halo, {name}!
        </p>
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
    </header>
  );
}
