"use client";

interface TimelinePhase {
  sequence: number;
  title: string;
  description: string;
}

interface Props {
  timeline: TimelinePhase[];
}

export function ProposalTimeline({ timeline }: Props) {
  if (timeline.length === 0) return null;

  return (
    <section className="mb-12 break-inside-avoid">
      <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-4">Alur Kerja & Timeline Pengerjaan</h2>
      <div className="bg-white border-2 border-zinc-200 rounded-2xl p-6 shadow-sm print:border-zinc-300 print:shadow-none">
        {/* Progress bar */}
        <div className="relative mb-6">
          <div className="h-2 bg-zinc-100 rounded-full">
            <div className="h-2 bg-amber-500 rounded-full transition-all duration-500" style={{ width: "8%" }}></div>
          </div>
          <div className="flex justify-between mt-2">
            <span className="text-[9px] text-amber-600 font-bold">Anda di sini</span>
            <span className="text-xs font-semibold text-zinc-500">Proyek Selesai</span>
          </div>
        </div>
        <div className="space-y-0">
          {timeline.map((phase, idx) => (
            <div key={idx} className="relative flex items-start gap-4 pb-5 last:pb-0">
              {idx < timeline.length - 1 && (
                <div className="absolute left-4 top-9 w-0.5 h-full bg-amber-200"></div>
              )}
              <div className="w-8 h-8 rounded-full bg-amber-500 text-white text-sm font-bold flex items-center justify-center shrink-0 mt-0.5 relative z-10 print:bg-amber-600">
                {phase.sequence}
              </div>
              <div className="flex-1 pb-4 border-b border-zinc-100 last:border-0">
                <h4 className="text-base font-bold text-zinc-900 print:text-black">{phase.title}</h4>
                <p className="text-sm text-zinc-600 leading-relaxed mt-1 print:text-zinc-700">{phase.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Print-only timeline format */}
      <div className="hidden print:block mt-4">
        <ol className="list-none space-y-2">
          {timeline.map((phase) => (
            <li key={phase.sequence} className="text-sm text-black">
              <span className="font-bold">[{phase.sequence}] - {phase.title}:</span> {phase.description}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}