"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { setUnauthorizedHandler } from "../lib/api";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import ProgressWidget from "./ProgressWidget";
import { AuthProvider } from "../contexts/AuthContext";

function LayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setUnauthorizedHandler(() => router.push("/login"));
  }, [router]);

  if (pathname === "/login" || pathname === "/login/" || pathname.startsWith("/proposal/") || pathname.startsWith("/report/") || pathname.startsWith("/client-report/")) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-canvas)]">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <TopBar onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto p-3 sm:p-6 bg-[var(--bg-canvas)]">
          {children}
        </main>
      </div>
      <ProgressWidget />
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
