"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { getUserInfo } from "../lib/api";

export default function TopBar() {
  const [name, setName] = useState("Admin");
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setName(getUserInfo().name);
    setMounted(true);
  }, []);

  return (
    <header className="h-14 shrink-0 bg-[var(--bg-surface)] border-b border-[var(--border-subtle)] flex items-center px-6 justify-between">
      <p className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
        Halo, {name}!
      </p>
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
