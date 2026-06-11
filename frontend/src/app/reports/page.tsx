"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ReportsPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/documents/reports"); }, [router]);
  return <div className="p-6 text-sm text-neutral-400">Mengalihkan...</div>;
}
