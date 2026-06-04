"use client";

import { useState } from "react";
import { Copy } from "lucide-react";

interface WASnippet {
  label: string;
  getText: () => string;
}

interface WASnippetDrawerProps {
  open: boolean;
  onClose: () => void;
  businessName?: string;
  purchasedProduct?: string;
  snippets: WASnippet[];
}

export default function WASnippetDrawer({
  open,
  onClose,
  businessName,
  purchasedProduct,
  snippets,
}: WASnippetDrawerProps) {
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm bg-[var(--bg-surface)] border-l border-[var(--border-default)] shadow-xl h-full overflow-y-auto">
        <div className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Laci Balasan Cepat WA</h3>
            <button onClick={onClose} className="p-1 text-neutral-400 hover:text-neutral-600">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <p className="text-xs text-neutral-500">Klik tombol untuk menyalin teks balasan ke clipboard, lalu paste ke WhatsApp.</p>

          <div className="space-y-3">
            {snippets.map((snippet, idx) => (
              <button
                key={idx}
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(snippet.getText());
                    setCopiedIdx(idx);
                    setTimeout(() => setCopiedIdx(null), 2000);
                  } catch {}
                }}
                className="w-full text-left p-3 rounded-lg border border-[var(--border-default)] hover:bg-green-50 dark:hover:bg-green-900/10 transition-colors group"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{snippet.label}</span>
                  {copiedIdx === idx ? (
                    <span className="text-xs text-green-600 font-medium">Disalin!</span>
                  ) : (
                    <Copy className="w-3.5 h-3.5 text-neutral-400 group-hover:text-green-500" />
                  )}
                </div>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2">{snippet.getText()}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export const WA_SNIPPETS = (businessName?: string, purchasedProduct?: string) => [
  {
    label: "Objection: Kemahalan",
    getText: () => `Pak, saya paham pertimbangannya. Tapi coba kita hitung bersama: setiap bulan ada ratusan calon pelanggan di kota Bapak yang mencari jasa ${purchasedProduct || "seperti bisnis Bapak"} di Google. Tanpa website yang teroptimasi, semua calon pelanggan itu lari ke kompetitor. Investasi perbaikan web ini jauh lebih kecil dibanding potensi omzet ratusan juta yang hilang setiap bulannya ke kompetitor. Ini bukan biaya, tapi investasi yang ROI-nya bisa dihitung langsung di kalkulator laporan audit kemarin.`,
  },
  {
    label: "Objection: Mau Diskusi Dulu",
    getText: () => `Silakan Pak, justru laporan itu sengaja saya desain rapi agar bisa Bapak share ke partner bisnis menggunakan tombol khusus di samping tombol WA utama halaman kemarin. Silakan ditinjau bersama kalkulator proyeksinya, besok siang saya kabari lagi ya Pak untuk slot wilayahnya.`,
  },
  {
    label: "Follow-Up: Belum Buka Link",
    getText: () => `Halo Pak, saya notice laporan audit digital untuk ${businessName || "bisnis Bapak"} belum dibuka. Laporan ini ada timer 24 jam untuk harga spesial. Mau saya kirim ulang linknya sekarang?`,
  },
  {
    label: "Closing: Konfirmasi Deal",
    getText: () => `Baik Pak, terima kasih atas kepercayaannya. Saya akan segera proses onboarding untuk ${businessName || "bisnis Bapak"}. Tim teknis kami akan mulai audit mendalam dalam 1x24 jam. Ada yang perlu ditanyakan sebelum kita mulai?`,
  },
];