"use client";

import { Suspense } from "react";

export default function SuspenseWrapper({ children, fallback }: { children: React.ReactNode; fallback?: React.ReactNode }) {
  return <Suspense fallback={fallback ?? <div className="flex items-center justify-center py-20"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-yellow" /></div>}>{children}</Suspense>;
}
