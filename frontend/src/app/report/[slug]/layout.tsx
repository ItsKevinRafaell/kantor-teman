import type { Metadata } from "next";

const SITE_URL = "https://kantorteman.my.id";
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  let title = "Laporan Audit Digital Gratis - Kantor Teman";
  let description = "Kami menemukan beberapa masalah kritis pada bisnis Anda yang membuat calon pelanggan lari ke kompetitor. Lihat laporan lengkapnya di sini.";
  const url = `${SITE_URL}/report/${params.slug}`;
  const ogImage = `${SITE_URL}/report/${params.slug}/opengraph-image`;

  try {
    const res = await fetch(`${API_BASE}/api/proposals/public/report/${params.slug}`, {
      next: { revalidate: 60 },
    });
    if (res.ok) {
      const data = await res.json();
      const businessName = data.nama_usaha || "";
      if (businessName) {
        title = `Hasil Audit Digital: ${businessName}`;
        description = `Laporan audit digital eksklusif untuk ${businessName}. Kami menemukan masalah kritis yang perlu segera ditangani sebelum kompetitor mengambil lebih banyak pelanggan Anda.`;
      }
    }
  } catch {
    // fallback to defaults
  }

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url,
      type: "article",
      siteName: "Kantor Teman",
      images: [{ url: ogImage, width: 1200, height: 630, alt: title }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [ogImage],
    },
  };
}

export default function ReportLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
