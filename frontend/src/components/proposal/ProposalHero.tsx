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
    <header className="mb-10 break-inside-avoid">
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
      <h1 className="text-3xl md:text-4xl font-black text-zinc-900 dark:text-white leading-tight print:text-black">
        Proposal Solusi Digital untuk {proposal.business_name || "Bisnis Anda"}
      </h1>
      <p className="mt-4 text-base md:text-lg font-semibold text-zinc-700 dark:text-zinc-300 leading-relaxed print:text-zinc-700">
        Rencana kerja praktis untuk membuat calon pelanggan lebih mudah menemukan, menilai, dan menghubungi bisnis Anda.
      </p>
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-2">
        {["Siap dieksekusi tim", "Fokus ke leads masuk", "Bisa dipantau bertahap"].map(item => (
          <div key={item} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/20 dark:text-amber-300">
            {item}
          </div>
        ))}
      </div>
      <p className="text-sm text-zinc-600 dark:text-zinc-400 font-medium mt-5 print:text-zinc-700">
        Disiapkan secara eksklusif oleh Tim Kantor Teman · {formatDate(proposal.created_at)}
      </p>
    </header>
  );
}
