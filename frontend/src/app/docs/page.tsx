"use client";

import { useState } from "react";
import { Search, Book, Users, FileText, Briefcase, Wallet, Megaphone, FolderOpen, Settings, Sparkles, ChevronRight } from "lucide-react";

interface DocSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  category: string;
  content: {
    apa: string;
    cara: string[];
    fitur: string[];
    tips?: string[];
    faq?: { q: string; a: string }[];
  };
}

const SECTIONS: DocSection[] = [
  {
    id: "login",
    title: "Login & Akun",
    category: "Mulai",
    icon: <Users size={16} />,
    content: {
      apa: "Halaman masuk ke sistem CRM. Setiap user punya akun sendiri dengan role admin atau member.",
      cara: [
        "Buka halaman login",
        "Masukkan email dan password",
        "Klik tombol Masuk",
        "Sistem akan redirect ke Dashboard",
      ],
      fitur: [
        "Auto-redirect kalau sudah login",
        "Logo brand kit otomatis tampil",
        "Cookie HttpOnly untuk keamanan",
        "Rate limit 5x percobaan / 5 menit",
      ],
      tips: [
        "Lupa password? Hubungi admin untuk reset.",
        "Jangan share akun — setiap action tercatat di Audit Log.",
      ],
    },
  },
  {
    id: "dashboard",
    title: "Dashboard",
    category: "Mulai",
    icon: <Book size={16} />,
    content: {
      apa: "Halaman utama yang menampilkan ringkasan bisnis: total leads, klien aktif, conversion rate, dan hot leads.",
      cara: [
        "Login → otomatis ke Dashboard",
        "Lihat 4 stat cards di atas",
        "Hot Leads = lead yang baru lihat proposal dalam 24 jam",
        "Top Scored = lead dengan score AI tertinggi",
      ],
      fitur: [
        "Auto-refresh setiap 60 detik",
        "Re-engagement alerts untuk lead yang hampir hilang",
        "Bar chart distribusi leads per produk",
      ],
    },
  },
  {
    id: "scraper",
    title: "Maps Scraper",
    category: "Akuisisi Leads",
    icon: <Search size={16} />,
    content: {
      apa: "Tool untuk scrape bisnis dari Google Maps berdasarkan kategori dan lokasi. Hasil otomatis tersimpan sebagai leads.",
      cara: [
        "Klik menu Maps Scraper di sidebar",
        "Isi kategori (contoh: 'restoran'), lokasi ('Jakarta Selatan'), dan max results",
        "Pilih product interest yang relevan",
        "Klik Scrape — leads akan masuk ke /contacts dengan rating Google",
        "AI Analysis aktif → tiap lead dapat pain points dan suggested product",
      ],
      fitur: [
        "Source: Google Places API (data resmi)",
        "Auto-deduplication berdasarkan phone number",
        "Batch name untuk grouping hasil scrape",
        "Riwayat scrape tersimpan dengan filter tanggal",
        "Concurrent limit untuk hindari rate limit",
      ],
      tips: [
        "Pakai kata kunci spesifik agar hasil relevan.",
        "Max 100 results per scrape — split kalau perlu lebih.",
        "Jangan scrape kategori yang sama dua kali — bakal duplicate.",
        "AI Analysis butuh AI provider configured di Settings → AI Engine.",
      ],
    },
  },
  {
    id: "leads",
    title: "Leads & Prospek",
    category: "Akuisisi Leads",
    icon: <Users size={16} />,
    content: {
      apa: "Daftar semua bisnis yang sudah di-scrape atau ditambahkan manual. Status leads dari Scraped → Contacted → Replied → Closed.",
      cara: [
        "Buka /contacts",
        "Filter berdasarkan status, batch, rating, atau score",
        "Klik nama bisnis untuk detail",
        "Update status manual atau lewat WA reply",
        "Klik Convert untuk jadikan klien (Contact) — wajib sebelum buat proposal",
      ],
      fitur: [
        "Lead score AI: Siap Closing (≥80), Perlu Pendekatan (50-79), Belum Match (<50)",
        "Tracking proposal views — lead yang buka proposal terdeteksi di Dashboard (Hot Leads)",
        "Bulk filter dan export CSV",
        "Map view untuk lihat sebaran geografis",
        "Soft-delete dengan restore button",
      ],
      tips: [
        "Score ≥80 (Siap Closing) = prioritas convert dan follow-up.",
        "Status Contacted otomatis update saat blast WA terkirim.",
        "Lead archived 30+ hari bisa di-purge admin.",
        "Pastikan AI provider sudah dikonfigurasi di Settings agar AI Analysis aktif saat scrape.",
      ],
    },
  },
  {
    id: "proposals",
    title: "Proposal",
    category: "Sales",
    icon: <FileText size={16} />,
    content: {
      apa: "Buat dan kirim proposal ke klien. Klien bisa accept/reject langsung dari link publik. Proposal accepted otomatis bikin Project + Board + Workspace.",
      cara: [
        "Convert lead dulu di /contacts → klien muncul di /clients",
        "Buka /clients → klik aksi pada klien → Buat Proposal",
        "Pilih services dan addons",
        "Set timeline (auto-generate dari template)",
        "Sistem hitung total + diskon (configurable di Settings)",
        "Copy link /p/{slug} → kirim ke klien via WA",
        "Klien klik Accept → admin dapat notifikasi WA, Project + Board + Workspace auto-created",
      ],
      fitur: [
        "Tracking pixel: tahu kapan klien buka proposal + durasi baca",
        "Discount countdown 24 jam",
        "FAQ otomatis (configurable)",
        "Social proof (jumlah klien yang sudah pakai)",
        "Public OG image untuk preview di WhatsApp",
        "Workspace auto-init hanya jika service_type punya template (web_dev, seo_gmaps, sosmed, dll)",
        "Soft-delete + restore",
      ],
      tips: [
        "Pakai timeline template SEO/web/sosmed sesuai service.",
        "Diskon dan FAQ default bisa diubah di Settings → AI Engine.",
        "Track view duration di /proposals untuk lihat keseriusan klien.",
      ],
    },
  },
  {
    id: "report",
    title: "Laporan Digital (Audit Report)",
    category: "Sales",
    icon: <FileText size={16} />,
    content: {
      apa: "Laporan audit digital untuk bisnis lokal. Dipakai sebagai pemikat sebelum kirim proposal.",
      cara: [
        "Dari detail lead → Generate Report",
        "AI buat analisis: pain points, kompetitor, saran produk",
        "Copy link /r/{slug} → kirim ke target",
        "Target lihat report → engagement tracked",
      ],
      fitur: [
        "Competitor count berdasarkan kategori + kota",
        "Monthly search volume estimate",
        "Pricing dengan discount timer",
        "City/province map",
        "Bot-aware OG meta tags (preview WA bagus)",
      ],
      tips: [
        "Kapan pakai Audit Report? Cold lead atau lead yang baru kenal — kasih hook value dulu sebelum kirim proposal.",
        "Lead Replied/Warm → langsung Proposal, skip Audit Report.",
        "Setelah target buka report, lead score otomatis naik (engagement signal).",
      ],
    },
  },
  {
    id: "clients",
    title: "Klien (Buku Klien)",
    category: "Klien",
    icon: <Users size={16} />,
    content: {
      apa: "Daftar klien aktif yang sudah convert dari leads. Track LTV, billing aktif, dana talangan, dan project ongoing.",
      cara: [
        "Buka /clients",
        "Klik klien untuk detail",
        "Tambah project (FIXED atau RETAINER)",
        "Catat notes per kategori (Bisnis/Teknis/Penting)",
        "Simpan kredensial klien (terenkripsi)",
        "Tambah link dokumen cloud",
      ],
      fitur: [
        "LTV calculator (FIXED + RETAINER × bulan)",
        "Active billing total",
        "Dana talangan = pengeluaran belum di-billing",
        "Notes timeline dengan filter kategori",
        "Credentials vault terenkripsi (Fernet)",
      ],
      tips: [
        "Retainer dihitung nominal × bulan jalan.",
        "Tag transaksi dengan client_id di /finance untuk track dana talangan.",
        "Dana talangan hilang setelah invoice digenerate yang reference transaksi tersebut.",
        "Kredensial otomatis encrypt saat simpan.",
      ],
    },
  },
  {
    id: "board",
    title: "Project Board (Kanban)",
    category: "Delivery",
    icon: <Briefcase size={16} />,
    content: {
      apa: "Trello-style kanban untuk track progress proyek per klien. Setiap project punya board sendiri.",
      cara: [
        "Buka /board",
        "Pilih project → board terbuka",
        "Tambah card di kolom To Do",
        "Drag card ke In Progress / Review / Done",
        "Klik card → tambah comment, checklist, due date",
      ],
      fitur: [
        "4 default columns: To Do, In Progress, Review, Done",
        "Card linked ke workspace row (2-way sync)",
        "Activity log per card",
        "Hanya admin bisa pindahkan card ke Done/Revisi",
        "Archive board untuk simpan, restore kapan saja",
      ],
      tips: [
        "Card yang linked ke workspace ga bisa diubah judulnya — edit di workspace.",
        "Pakai labels untuk priority (urgent, blocked, dll).",
      ],
    },
  },
  {
    id: "workspace",
    title: "Workspace (Spreadsheet)",
    category: "Delivery",
    icon: <Briefcase size={16} />,
    content: {
      apa: "Workspace mirip Notion table per project. Data per bulan untuk retainer (SEO, sosmed, dll). Auto-sync dengan Board.",
      cara: [
        "Project dibuat → workspace auto-init dari template service_type",
        "Buka /workspace → pilih project",
        "Edit cell langsung (status, due date, link, dll)",
        "Status berubah → card di Board ikut pindah kolom",
      ],
      fitur: [
        "Service templates: web_dev, seo_gmaps, sosmed, maintenance, branding",
        "Multi-sheet (per bulan untuk retainer)",
        "Custom column types (text, number, date, select, checkbox)",
        "Attachment upload per row",
        "Auto-prompt invoice saat task 'Invoice pembayaran X%' di-mark Done",
      ],
      tips: [
        "Project Selesai? Mark semua tasks Done → generate invoice final via Document Generator → archive project di /clients.",
        "Mark task 'Invoice pembayaran 30%/40%' jadi Done → muncul modal konfirmasi auto-generate invoice.",
        "Jangan hapus row template — data per bulan akan hilang.",
      ],
    },
  },
  {
    id: "finance",
    title: "Keuangan",
    category: "Operasional",
    icon: <Wallet size={16} />,
    content: {
      apa: "Multi-wallet finance tracker. Catat income/expense, hitung BEP, financial runway, dan track outreach cost.",
      cara: [
        "Buka /finance",
        "Tambah wallet (Bank, E-wallet, Cash)",
        "Catat transaksi (income/expense + kategori)",
        "Tag transaksi dengan klien untuk dana talangan",
        "Lihat reports: balance, BEP, runway",
      ],
      fitur: [
        "Auto wallet balance update",
        "Soft-delete + restore transaksi",
        "Export CSV",
        "Outreach cost analytics (CPA, ROI per campaign)",
        "Provider quota tracking (Fonnte, AI)",
      ],
      tips: [
        "BEP = total expense bulanan — perlu revenue minimal sebanyak ini.",
        "Runway = balance ÷ pengeluaran bulanan, dalam bulan.",
      ],
    },
  },
  {
    id: "subscriptions",
    title: "Langganan (Subscriptions)",
    category: "Operasional",
    icon: <Wallet size={16} />,
    content: {
      apa: "Track recurring expenses bulanan/tahunan. Klik tombol tiap awal bulan untuk catat pengeluaran otomatis ke wallet.",
      cara: [
        "Buka /finance/subscriptions",
        "Tambah langganan (nama, jumlah, billing cycle, next date)",
        "Tiap awal bulan → klik 'Catat Pengeluaran Bulan Ini'",
        "Sistem buat expense transaction + update next billing date",
      ],
      fitur: [
        "Billing cycle: monthly, yearly, weekly, daily",
        "Days-until countdown",
        "One-click batch deduct semua yang jatuh tempo",
      ],
    },
  },
  {
    id: "blast",
    title: "WA Blast",
    category: "Marketing",
    icon: <Megaphone size={16} />,
    content: {
      apa: "Kirim WhatsApp massal ke leads via Fonnte API. Track delivery, read, reply, dan conversion funnel.",
      cara: [
        "Filter leads di /contacts (status, batch, product)",
        "Klik Blast → pilih template",
        "Set jadwal atau kirim sekarang",
        "Monitor di /marketing/blast-analytics",
      ],
      fitur: [
        "Funnel tracking: Sent → Delivered → Read → Replied → Closed",
        "Per-template performance stats",
        "Webhook auto-update status saat klien reply",
        "Schedule blast via APScheduler",
        "Cost tracking per campaign",
      ],
      tips: [
        "Pakai variable {{business_name}}, {{client_name}} di template.",
        "Reply rate >5% sudah bagus untuk cold outreach.",
        "Jangan blast >100 nomor sekaligus — risk WA banned.",
      ],
    },
  },
  {
    id: "followup",
    title: "Follow-up Otomatis",
    category: "Marketing",
    icon: <Megaphone size={16} />,
    content: {
      apa: "Sequence pesan otomatis ke leads yang belum reply. Sistem auto-stop kalau lead sudah reply.",
      cara: [
        "Dari detail lead → Start Follow-up",
        "Pilih template_ids urut (3 step default)",
        "Set delays (contoh: [1, 3, 7] hari)",
        "Sistem kirim otomatis tiap 30 menit (cron)",
      ],
      fitur: [
        "Auto-stop kalau lead sudah reply (cek BlastMessage.replied_at)",
        "Multi-step sequence (max 7 steps)",
      ],
      tips: [
        "Sequence tidak bisa di-resume setelah di-stop — start ulang dari detail lead jika perlu.",
        "Cron jalan tiap 30 menit — pesan tidak langsung terkirim saat jadwal.",
      ],
    },
  },
  {
    id: "ads",
    title: "Iklan & Kampanye",
    category: "Marketing",
    icon: <Megaphone size={16} />,
    content: {
      apa: "Track campaign iklan berbayar (Meta Ads, Google Ads). Status PLANNING → ACTIVE → COMPLETED.",
      cara: [
        "Buka /marketing/ads",
        "Tambah campaign (nama, target audience, budget, drive link)",
        "Set status ACTIVE → expense otomatis tercatat di wallet 'Dompet Budget Ads'",
        "Update leads_count + conversions_count manual",
      ],
      fitur: [
        "Auto-create wallet 'Dompet Budget Ads'",
        "CPA dan cost per lead calculator",
        "Drive link untuk kreatif materials",
      ],
    },
  },
  {
    id: "calendar",
    title: "Kalender Konten",
    category: "Marketing",
    icon: <Megaphone size={16} />,
    content: {
      apa: "Schedule konten sosial media bulanan. Optional sync ke Google Calendar.",
      cara: [
        "Buka /marketing/calendar",
        "Klik tanggal → tambah konten",
        "Pilih type: IG Carousel, Reels, SEO Article, TikTok, YouTube",
        "Status: DRAFT → SCHEDULED → PUBLISHED",
      ],
      fitur: [
        "Custom content types dengan color labels",
        "Google Calendar sync (perlu setup di Settings)",
        "Monthly view dengan drag-drop",
      ],
    },
  },
  {
    id: "content-generator",
    title: "Content Generator (AI)",
    category: "AI Tools",
    icon: <Sparkles size={16} />,
    content: {
      apa: "Generate konten dengan AI: SEO article + image. Pakai session untuk continuity antar generation.",
      cara: [
        "Buka /content-generator",
        "Pilih tool: SEO Article atau Image",
        "Buat session baru atau pilih existing",
        "Isi prompt + parameter",
        "Klik Generate",
      ],
      fitur: [
        "SEO Article: search intent, keyword difficulty, SERP features, LSI keywords",
        "Image generator: configurable provider/model",
        "Session context carries previous generations",
        "Publish article ke CMS langsung",
        "Markdown rendering inline",
      ],
      tips: [
        "Configure providers di /content-generator → Settings",
        "Image generation timeout 120 detik",
        "Pakai session berbeda untuk topik berbeda",
      ],
    },
  },
  {
    id: "ai-chat",
    title: "AI Chat (Asisten Bisnis)",
    category: "AI Tools",
    icon: <Sparkles size={16} />,
    content: {
      apa: "AI assistant untuk diskusi bisnis. Bisa query data CRM langsung (RAG), tool calling, dan persistent memory.",
      cara: [
        "Buka /chat",
        "Buat project baru (kasih system prompt)",
        "Pilih model dari dropdown",
        "Mulai chat — AI bisa akses leads, transactions, dll",
        "Pin pesan penting jadi memory",
      ],
      fitur: [
        "Multi-project, multi-conversation",
        "RAG: AI auto-query DB tables relevant",
        "Tool calling: create_lead, search_leads, send_whatsapp, etc",
        "Memory persists across conversations",
        "Auto-summarization tiap 10 messages",
        "Fullscreen toggle",
      ],
      tips: [
        "AI bisa kirim WA otomatis via tool send_whatsapp — review prompt dan pastikan konteks benar sebelum aktifkan.",
        "Pakai project terpisah untuk topik berbeda agar memory tidak tercampur.",
      ],
    },
  },
  {
    id: "documents",
    title: "Dokumen & Arsip",
    category: "Dokumen",
    icon: <FolderOpen size={16} />,
    content: {
      apa: "Foldering system untuk simpan notes dan link dokumen. Mirip Notion lite.",
      cara: [
        "Buka /documents",
        "Buat folder dengan warna",
        "Tambah dokumen (notes atau external URL)",
        "Tag untuk searchability",
      ],
      fitur: [
        "Nested folders dengan colored labels",
        "Rich text body atau external URL",
        "Search across all docs",
        "Tags untuk grouping",
      ],
    },
  },
  {
    id: "doc-generator",
    title: "Generator Dokumen (Invoice, Kontrak)",
    category: "Dokumen",
    icon: <FileText size={16} />,
    content: {
      apa: "Generate PDF dari template HTML. Untuk invoice, proposal PDF, kontrak, surat penawaran.",
      cara: [
        "Buka /documents/generator → New",
        "Step 1: Pilih template",
        "Step 2: Pilih target (klien atau kosong)",
        "Step 3: Isi variables",
        "Step 4: Preview",
        "Step 5: Done — download atau email",
      ],
      fitur: [
        "Template types: invoice, proposal_pdf, kontrak, surat_penawaran, custom",
        "Brand kit auto-injected (logo, colors, fonts)",
        "Tracking pixel embedded — tahu kapan dibuka",
        "Email delivery via SMTP",
        "Jinja2 templating",
      ],
    },
  },
  {
    id: "brand-kit",
    title: "Brand Kit",
    category: "Master Data",
    icon: <Settings size={16} />,
    content: {
      apa: "Single source of truth untuk identitas brand: logos, warna, font, tagline.",
      cara: [
        "Buka /master/brand-kit (admin only)",
        "Upload logo primary, secondary, brandmark",
        "Tambah warna palette",
        "Set font + tagline",
      ],
      fitur: [
        "Logo otomatis tampil di Sidebar, Login, PWA icon",
        "Brandmark = favicon",
        "Allowed: PNG, JPG, JPEG, WEBP, ICO, SVG",
        "Max 2MB per file",
        "Public endpoint /api/brand-kit/public (no auth)",
      ],
    },
  },
  {
    id: "master-data",
    title: "Data Master (Produk, Kategori, Template)",
    category: "Master Data",
    icon: <Settings size={16} />,
    content: {
      apa: "Konfigurasi produk yang dijual, kategori, dan template pesan.",
      cara: [
        "/master/products — katalog layanan/produk",
        "/master/categories — grouping produk",
        "/master/templates — template pesan WA Blast, Proposal, Follow-up",
      ],
      fitur: [
        "Product types: FIXED atau RETAINER",
        "ROI calculator per produk (months, multiplier)",
        "Template variables: {{client_name}}, {{business_name}}, etc",
        "Per-template stats: reply rate, conversion rate",
      ],
    },
  },
  {
    id: "vault",
    title: "Brankas Internal",
    category: "Master Data",
    icon: <Settings size={16} />,
    content: {
      apa: "Vault terenkripsi untuk simpan kredensial internal (API keys, passwords, tokens) yang BUKAN milik klien.",
      cara: [
        "Buka /master/internal-vault",
        "Tambah credential (kategori, title, fields)",
        "Mark field sebagai secret → encrypted di DB",
        "Copy value dengan satu klik",
      ],
      fitur: [
        "Fernet encryption (AES symmetric)",
        "Categories: WordPress, Google, Server, Email, etc",
        "Field-level secret toggle",
        "Show/hide values",
      ],
      tips: [
        "Jangan share screenshot — copy via tombol Copy.",
        "Kredensial klien simpan di /clients, bukan di sini.",
      ],
    },
  },
  {
    id: "costs",
    title: "Biaya & Kuota",
    category: "Marketing",
    icon: <Wallet size={16} />,
    content: {
      apa: "Dashboard untuk monitor sisa kuota provider (Fonnte, AI) dan estimate balance bulanan.",
      cara: [
        "Buka /marketing/costs",
        "Lihat remaining quota Fonnte, Gemini, Claude, OpenAI",
        "Top-up quota saat habis",
        "Reset error status setelah top-up",
      ],
      fitur: [
        "Per-campaign operational cost",
        "ROI dan CPA per campaign",
        "Provider configs editable",
      ],
    },
  },
  {
    id: "settings",
    title: "Pengaturan & Integrasi",
    category: "System",
    icon: <Settings size={16} />,
    content: {
      apa: "Konfigurasi global sistem: profil user, AI provider, integrasi (Fonnte, Google, SMTP), audit logs.",
      cara: [
        "Buka /settings",
        "Tab Profile: ganti nama, password",
        "Tab AI Engine: konfigurasi AI provider/model",
        "Tab Integrasi: Fonnte token, Google API, SMTP, follow-up schedule",
        "Tab Audit Logs: riwayat aksi user",
      ],
      fitur: [
        "Multi-provider AI (OpenAI, Claude, Gemini)",
        "External lead API key untuk webhook",
        "Auto follow-up schedule (jam)",
        "Audit log filterable",
      ],
      tips: [
        "Simpan API key di Settings, BUKAN di .env (lebih aman).",
        "Audit log retain 90 hari (hardcoded).",
      ],
    },
  },
  {
    id: "reports",
    title: "Laporan & Analitik",
    category: "System",
    icon: <FileText size={16} />,
    content: {
      apa: "Halaman ringkasan performa bisnis: conversion funnel, revenue trend, dan lead source analytics.",
      cara: [
        "Buka /reports dari sidebar",
        "Lihat overview: total leads, conversion rate, revenue",
        "Filter berdasarkan periode",
        "Export data jika diperlukan",
      ],
      fitur: [
        "Conversion funnel visualization",
        "Lead source breakdown",
        "Revenue per service type",
        "Period comparison",
      ],
    },
  },
  {
    id: "tasks",
    title: "Background Tasks",
    category: "System",
    icon: <Settings size={16} />,
    content: {
      apa: "Monitor background jobs yang sedang berjalan: scraping, AI analysis, follow-up scheduler, blast queue.",
      cara: [
        "Buka /tasks dari sidebar",
        "Lihat daftar task yang running/completed/failed",
        "Klik task untuk detail + error log",
        "Retry failed tasks jika diperlukan",
      ],
      fitur: [
        "Real-time status update",
        "Error log per task",
        "Auto-cleanup completed tasks setelah 24 jam",
      ],
    },
  },
  {
    id: "roles",
    title: "Role & Akses",
    category: "System",
    icon: <Users size={16} />,
    content: {
      apa: "Sistem role-based access: Admin punya akses penuh, Member dibatasi pada fitur tertentu.",
      cara: [
        "Admin buat akun member di Settings",
        "Member login dengan akun sendiri",
        "Aksi member tercatat di Audit Log",
      ],
      fitur: [
        "Admin: full access — settings, brand kit, delete, move card ke Done/Revisi, create project dari board",
        "Member: bisa lihat leads, clients, board, workspace — tidak bisa delete, ubah settings, atau akses brand kit",
        "Sidebar otomatis hide menu admin-only untuk member",
        "Setiap aksi tercatat di Audit Log dengan nama actor",
      ],
      tips: [
        "Buat akun member untuk tim operasional — mereka bisa update status tanpa risiko hapus data.",
        "Admin tetap bisa lihat semua aksi member di Audit Logs.",
      ],
    },
  },
];

const CATEGORIES = ["Mulai", "Akuisisi Leads", "Sales", "Klien", "Delivery", "Operasional", "Marketing", "AI Tools", "Dokumen", "Master Data", "System"];

export default function DocsPage() {
  const [search, setSearch] = useState("");
  const [activeId, setActiveId] = useState<string>(SECTIONS[0].id);

  const filtered = SECTIONS.filter(s => {
    if (!search) return true;
    const q = search.toLowerCase();
    return s.title.toLowerCase().includes(q) ||
      s.content.apa.toLowerCase().includes(q) ||
      s.content.fitur.some(f => f.toLowerCase().includes(q));
  });

  const active = SECTIONS.find(s => s.id === activeId) || SECTIONS[0];

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-120px)]">
        {/* Sidebar */}
        <aside className="lg:w-72 shrink-0 flex flex-col gap-4">
          <div>
            <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-50">Dokumentasi</h1>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">Panduan lengkap setiap modul</p>
          </div>

          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              id="docs-search"
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Cari modul..."
              className="w-full pl-9 pr-3 py-2 text-sm bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-yellow/50"
            />
          </div>

          <nav className="flex-1 overflow-y-auto -mx-2">
            {CATEGORIES.map(cat => {
              const items = filtered.filter(s => s.category === cat);
              if (items.length === 0) return null;
              return (
                <div key={cat} className="mb-3">
                  <p className="px-3 mb-1 text-[10px] font-bold uppercase tracking-widest text-neutral-400/70 dark:text-neutral-600">
                    {cat}
                  </p>
                  {items.map(s => (
                    <button
                      key={s.id}
                      onClick={() => setActiveId(s.id)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-colors text-left ${
                        activeId === s.id
                          ? "bg-brand-yellow/10 text-brand-yellow font-semibold"
                          : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                      }`}
                    >
                      {s.icon}
                      <span className="flex-1 truncate">{s.title}</span>
                      {activeId === s.id && <ChevronRight size={14} />}
                    </button>
                  ))}
                </div>
              );
            })}
          </nav>
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-y-auto bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-6 sm:p-8">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-bold uppercase tracking-widest text-brand-yellow">
              {active.category}
            </span>
          </div>
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50 mb-4">{active.title}</h2>

          <section className="mb-6">
            <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 dark:text-neutral-400 mb-2">Apa ini?</h3>
            <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">{active.content.apa}</p>
          </section>

          <section className="mb-6">
            <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 dark:text-neutral-400 mb-3">Cara Kerja</h3>
            <ol className="space-y-2">
              {active.content.cara.map((step, i) => (
                <li key={i} className="flex gap-3 text-sm text-neutral-700 dark:text-neutral-300">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-brand-yellow/10 text-brand-yellow text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <span className="pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
          </section>

          <section className="mb-6">
            <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 dark:text-neutral-400 mb-3">Fitur Utama</h3>
            <ul className="grid sm:grid-cols-2 gap-2">
              {active.content.fitur.map((f, i) => (
                <li key={i} className="flex gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                  <span className="text-emerald-500 mt-0.5">✓</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </section>

          {active.content.tips && (
            <section className="mb-6 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30 rounded-xl p-4">
              <h3 className="text-xs font-bold uppercase tracking-widest text-amber-700 dark:text-amber-400 mb-2">Tips & Catatan</h3>
              <ul className="space-y-1.5">
                {active.content.tips.map((tip, i) => (
                  <li key={i} className="text-sm text-amber-900 dark:text-amber-200">• {tip}</li>
                ))}
              </ul>
            </section>
          )}

          {active.content.faq && (
            <section className="mb-6">
              <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 dark:text-neutral-400 mb-3">Pertanyaan Umum</h3>
              <div className="space-y-3">
                {active.content.faq.map((item, i) => (
                  <div key={i}>
                    <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">{item.q}</p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{item.a}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
