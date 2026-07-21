"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { setUnauthorizedHandler } from "../lib/api";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import ProgressWidget from "./ProgressWidget";
import GlobalSearch from "./GlobalSearch";
import { AuthProvider } from "../contexts/AuthContext";

const DESKTOP_SIDEBAR_KEY = "kt_desktop_sidebar_collapsed";

function LayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    setUnauthorizedHandler(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    try {
      setDesktopCollapsed(localStorage.getItem(DESKTOP_SIDEBAR_KEY) === "1");
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const isMod = e.metaKey || e.ctrlKey;
      if (isMod && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function toggleDesktopSidebar() {
    setDesktopCollapsed(prev => {
      const next = !prev;
      try { localStorage.setItem(DESKTOP_SIDEBAR_KEY, next ? "1" : "0"); } catch { /* ignore */ }
      return next;
    });
  }

  if (pathname === "/login" || pathname === "/login/" || pathname.startsWith("/proposal/") || pathname.startsWith("/report/") || pathname.startsWith("/client-report/")) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-canvas)]">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        desktopCollapsed={desktopCollapsed}
        onToggleDesktop={toggleDesktopSidebar}
      />
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <TopBar
          onMenuClick={() => setSidebarOpen(true)}
          onSearchClick={() => setSearchOpen(true)}
          onToggleDesktopSidebar={toggleDesktopSidebar}
          desktopSidebarCollapsed={desktopCollapsed}
        />
        <main className="flex-1 overflow-y-auto p-3 sm:p-6 bg-[var(--bg-canvas)]">
          {children}
        </main>
      </div>
      <ProgressWidget />
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <LayoutContent>{children}</LayoutContent>
    </AuthProvider>
  );
}
