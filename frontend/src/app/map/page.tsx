"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function MapPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/leads?tab=peta"); }, [router]);
  return <div className="p-6 text-sm text-neutral-400">Mengalihkan...</div>;
}
