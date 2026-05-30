"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function ContactsRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const batch = searchParams.get("batch");
  const highlight = searchParams.get("highlight");

  useEffect(() => {
    const params = new URLSearchParams({ tab: "tabel" });
    if (batch) params.set("batch", batch);
    if (highlight) params.set("highlight", highlight);
    router.replace(`/leads?${params}`);
  }, [router, batch, highlight]);

  return <div className="p-6 text-sm text-neutral-400">Mengalihkan...</div>;
}

export default function ContactsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-neutral-400">Memuat...</div>}>
      <ContactsRedirect />
    </Suspense>
  );
}
