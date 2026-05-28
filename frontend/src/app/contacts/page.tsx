"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";

const LeadsTable = dynamic(() => import("../../components/LeadsTable"), { ssr: false });

function ContactsContent() {
  const searchParams = useSearchParams();
  const initialBatch = searchParams.get("batch") || undefined;

  return (
    <div className="max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-neutral-50">Semua Kontak</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Kelola semua leads dan update status follow-up.</p>
      </div>
      <LeadsTable initialBatch={initialBatch} />
    </div>
  );
}

export default function ContactsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-neutral-400">Memuat...</div>}>
      <ContactsContent />
    </Suspense>
  );
}
