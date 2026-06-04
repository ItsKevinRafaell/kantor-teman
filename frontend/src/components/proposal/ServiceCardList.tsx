"use client";

import { formatRupiah } from "../../utils/formatter";

interface ServiceItem {
  name: string;
  price: number;
  features: string[];
}

interface Props {
  services: ServiceItem[];
}

const SERVICE_BENEFITS: Record<string, string[]> = {
  "seo": [
    "Memastikan bisnis Anda ditemukan di halaman #1 saat calon pelanggan lokal siap membeli",
    "Menghemat biaya iklan berbayar jangka panjang dengan trafik organik stabil",
    "Meningkatkan kepercayaan calon pelanggan karena posisi teratas Google",
  ],
  "google maps": [
    "Bisnis Anda muncul pertama saat orang sekitar mencari jasa Anda di Maps",
    "Ulasan positif terkelola meningkatkan konversi hingga 3x lipat",
    "Calon pelanggan bisa langsung klik telepon/navigasi ke lokasi Anda",
  ],
  "website": [
    "Mengubah 70% pengunjung HP menjadi calon pembeli yang siap menghubungi",
    "Sistem navigasi instan tanpa lemot — loading di bawah 2 detik",
    "Tampilan profesional yang membangun kepercayaan sejak detik pertama",
  ],
  "landing page": [
    "Halaman khusus yang dirancang satu tujuan: mengkonversi pengunjung jadi leads",
    "Terintegrasi langsung dengan WhatsApp untuk respon instan",
    "Optimasi untuk iklan berbayar — setiap rupiah iklan lebih efektif",
  ],
  "instagram": [
    "Feed & story yang konsisten membangun personal branding profesional",
    "Auto-reply AI untuk menangkap setiap DM leads tanpamiss",
    "Visual system yang membuat brand Anda terlihat enterprise-grade",
  ],
  "content": [
    "Konten bulanan yang SEO-optimized untuk bangun otoritas di Google",
    "Calendar konten 30 hari yang siap dieksekusi tanpa perlu brainstorming",
    "Template caption viral yang sudah proven untuk industri Anda",
  ],
  "ads": [
    "Pixel setup & audience targeting yang akurat",
    "Campaign yang langsung menghasilkan leads, bukan sekadar impress",
    "Retargeting system untuk tangkap leads yang sudah pernah lihat bisnis Anda",
  ],
  "wa automation": [
    "Chatbot yang handle 90% pertanyaan umum klien — Anda fokus closing",
    "Auto-reply that feels personal, bukan bot generik",
    "Tag & follow-up otomatis — tidak ada leads yang terlewat",
  ],
};

const SERVICE_DESCRIPTIONS: Record<string, string> = {
  "seo": "Mengoptimalkan website Anda agar muncul di halaman pertama Google untuk kata kunci yang relevan dengan bisnis Anda.",
  "google maps": "Memaksimalkan visibilitas bisnis Anda di Google Maps agar mudah ditemukan oleh calon pelanggan di sekitar lokasi Anda.",
  "website": "Website profesional yang cepat, responsive, dan optimized untuk konversi pengunjung menjadi leads.",
  "landing page": "Halaman landing yang dirancang khusus untuk mengkonversi traffic iklan menjadi leads berkualitas.",
  "instagram": "Manajemen dan growth akun Instagram bisnis dengan konten yang engaging dan consistently branded.",
  "content": "Konten marketing bulanan yang SEO-optimized dan relevant dengan target audiens Anda.",
  "ads": "Campaign iklan berbayar yang targeted dan optimized untuk menghasilkan ROI positif.",
  "wa automation": "Otomatisasi WhatsApp untuk respons cepat dan follow-up leads yang efektif.",
};

function getBenefits(serviceName: string): string[] {
  const key = serviceName.toLowerCase();
  return SERVICE_BENEFITS[key] || [
    "Solusi lengkap untuk kebutuhan bisnis Anda",
    "Tim ahli yang berpengalaman di bidangnya",
    "Hasil yang terukur dan bisa dimonitor",
  ];
}

function getServiceDescription(serviceName: string): string {
  return SERVICE_DESCRIPTIONS[serviceName.toLowerCase()] || "Layanan profesional yang disesuaikan dengan kebutuhan bisnis Anda.";
}

export function ServiceCardList({ services }: Props) {
  return (
    <section className="space-y-4 mb-12">
      <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-2">Solusi yang Kami Siapkan untuk Anda</h2>
      <div className="grid grid-cols-1 gap-4">
        {services.map((service, i) => {
          const benefits = getBenefits(service.name);
          const description = getServiceDescription(service.name);
          return (
            <div
              key={i}
              className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 shadow-sm transition-all duration-300 ease-in-out hover:shadow-md hover:border-amber-500 break-inside-avoid print:border-zinc-300 print:shadow-none"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <h3 className="text-lg font-bold text-zinc-900 dark:text-white print:text-black">{service.name}</h3>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1 leading-relaxed print:text-zinc-700">{description}</p>
                </div>
                <span className="shrink-0 text-sm font-bold text-amber-600 whitespace-nowrap print:text-amber-700">
                  {formatRupiah(service.price)}
                </span>
              </div>
              <div className="border-t-2 border-zinc-100 pt-3 mt-3 print:border-zinc-200">
                <p className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-2">Dampak Langsung ke Bisnis Anda</p>
                <ul className="space-y-1.5">
                  {benefits.map((b, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-zinc-700 print:text-zinc-800">
                      <svg className="w-4 h-4 text-amber-500 mt-0.5 shrink-0 print:text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}