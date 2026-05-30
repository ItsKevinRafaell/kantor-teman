"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdsPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/marketing/campaigns?tab=campaigns"); }, [router]);
  return <div className="p-6 text-sm text-neutral-400">Mengalihkan...</div>;
}
