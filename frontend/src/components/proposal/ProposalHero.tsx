"use client";

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

interface ProposalHeroProps {
  proposal: {
    status: string;
    business_name: string | null;
    created_at: string | null;
    accepted_at?: string | null;
  };
}

export default function ProposalHero({ proposal }: ProposalHeroProps) {
  return (
    <header className="text-center mb-12 break-inside-avoid">
      {proposal.status === "accepted" ? (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-100 dark:bg-green-900/30 border-2 border-green-400 dark:border-green-700 mb-5">
          <svg className="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
          <span className="text-xs font-bold text-green-700 dark:text-green-400">Diterima pada {formatDate(proposal.accepted_at || null)}</span>
        </div>
      ) : proposal.status === "rejected" ? (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 border-2 border-zinc-300 dark:border-zinc-600 mb-5">
          <span className="text-xs font-bold text-zinc-500 dark:text-zinc-400">Penawaran Ditolak</span>
        </div>
      ) : (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-100 dark:bg-amber-900/30 border-2 border-amber-400 dark:border-amber-700 mb-5">
          <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
          <span className="text-xs font-bold text-amber-700 dark:text-amber-400">Penawaran Aktif</span>
        </div>
      )}
      <h1 className="text-2xl md:text-3xl font-black text-zinc-900 dark:text-white leading-tight print:text-black">
        Proposal Solusi &amp; Proyeksi Pertumbuhan Digital
      </h1>
      <p className="text-xl md:text-2xl font-black text-amber-600 mt-2 print:text-amber-700">
        {proposal.business_name}
      </p>
      <p className="text-sm text-zinc-600 dark:text-zinc-400 font-medium mt-4 print:text-zinc-700">
        Disiapkan secara eksklusif oleh Tim Kantor Teman · {formatDate(proposal.created_at)}
      </p>
    </header>
  );
}