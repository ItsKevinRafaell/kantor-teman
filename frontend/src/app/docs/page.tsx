"use client";

import { useState, useEffect } from "react";
import { Search, Book, Users, FileText, Briefcase, Wallet, Megaphone, FolderOpen, Settings, Sparkles, ChevronRight, GitBranch, Send, ClipboardList, CheckCircle2, LayoutGrid, Package, RefreshCw, Zap, Check } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { apiFetch } from "../../lib/api";

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

const PIPELINE_STAGES: {
  id: string; label: string; sub: string; Icon: LucideIcon;
  colorClass: string; bgClass: string; borderClass: string;
  trigger: string; output: string; ai: string; manual: string;
  flow: string; nextHint: string;
  badge: string | null; link: string;
}[] = [
  {
    id: "scrape", label: "Scrape", sub: "Google Maps", Icon: Search,
    colorClass: "text-blue-500", bgClass: "bg-blue-500/10", borderClass: "border-blue-500/30",
    trigger: "Manual — admin pilih kategori + kota di Maps Scraper",
    output: "Leads baru: nama bisnis, nomor WA, alamat, rating Google",
    ai: "Auto-score 40–85 berdasarkan rating, ada/tidaknya website, jumlah review",
    manual: "Pilih kategori, lokasi, max results, product interest",
    flow: "Mulai dari sini saat butuh prospek baru. Pilih kategori bisnis (mis. 'klinik gigi') + kota target, sistem scrape Google Maps → simpan ke daftar Leads. Setiap lead langsung dapat skor AI awal.",
    nextHint: "Lanjut ke Leads untuk filter & kelola hasil scrape.",
    badge: null, link: "/scraper",
  },
  {
    id: "leads", label: "Leads", sub: "CRM Pipeline", Icon: Users,
    colorClass: "text-purple-500", bgClass: "bg-purple-500/10", borderClass: "border-purple-500/30",
    trigger: "Auto dari scraper atau input manual",
    output: "Lead dengan status: Scraped → Contacted → HOT_PROSPECT → Closed/Client",
    ai: "Lead scoring otomatis + AI analysis (pain points, suggested product)",
    manual: "Update status, rating, product interest",
    flow: "Tahap kurasi. Filter lead skor tinggi (≥80 = Siap Closing), baca pain points hasil AI, tandai produk yang relevan. Lead yang sudah 'matang' dikirim WA Blast atau langsung dibuatkan proposal.",
    nextHint: "Cold lead → kirim WA Blast atau Audit Report dulu. Warm lead → langsung Proposal.",
    badge: "Auto-score", link: "/contacts",
  },
  {
    id: "blast", label: "Blast WA", sub: "Fonnte API", Icon: Send,
    colorClass: "text-green-500", bgClass: "bg-green-500/10", borderClass: "border-green-500/30",
    trigger: "Manual — admin pilih template + filter leads",
    output: "WA terkirim dengan link report publik, status → BLASTED",
    ai: "Template personalisasi {{business_name}}, {{proposal_link}}",
    manual: "Pilih template, filter leads, klik blast",
    flow: "Outreach awal. Pilih segmen lead, pilih template (variabel auto-isi nama bisnis), kirim. Sistem track delivery, read, dan reply. Lead yang reply pindah otomatis ke status REPLIED. Followup sequence auto-stop kalau lead sudah balas.",
    nextHint: "Yang buka Audit Report = sinyal hangat → siapkan Proposal.",
    badge: "Followup auto", link: "/marketing/blast-analytics",
  },
  {
    id: "report", label: "Report", sub: "Halaman Publik", Icon: FileText,
    colorClass: "text-orange-500", bgClass: "bg-orange-500/10", borderClass: "border-orange-500/30",
    trigger: "Lead klik link report di pesan WA",
    output: "Lead score naik, status → REPORT_VIEWED → HOT_PROSPECT",
    ai: "Pain Box, ROI Slider, FOMO Timer 24 jam, Ghost Viewer detection",
    manual: "Tidak ada — fully automated tracking",
    flow: "Hook value sebelum jual. Audit digital singkat untuk lead cold yang belum kenal. Semua engagement (durasi baca, scroll depth) tercatat. Skor lead naik otomatis kalau report dibuka.",
    nextHint: "Setelah report dibuka 1–2 kali, lanjut ke Proposal.",
    badge: "Ghost viewer", link: "/proposals",
  },
  {
    id: "proposal", label: "Proposal", sub: "Multi-service", Icon: ClipboardList,
    colorClass: "text-amber-500", bgClass: "bg-amber-500/10", borderClass: "border-amber-500/30",
    trigger: "Admin buat proposal dari halaman Klien",
    output: "Link publik /p/{slug} + analytics waktu baca per section",
    ai: "Auto-detect service type, contract months, nama project",
    manual: "Pilih layanan, set harga, kirim link ke prospect",
    flow: "Penawaran resmi. Dua jalur: (1) Proposal interaktif dengan tombol Accept — klien klik, sistem auto-create Project + Board + Workspace. (2) Surat penawaran legal manual — generate PDF dari Document Generator, tanda tangan, lalu admin buat workspace manual setelah deal.",
    nextHint: "Klien Accept → otomatis lompat ke tahap Close. Manual deal → buat project di /clients sendiri.",
    badge: "2 jalur", link: "/proposals",
  },
  {
    id: "close", label: "Close", sub: "Accept → Project", Icon: CheckCircle2,
    colorClass: "text-red-500", bgClass: "bg-red-500/10", borderClass: "border-red-500/30",
    trigger: "Klien klik Accept di halaman proposal publik",
    output: "Contact + Project + Board kanban auto-created",
    ai: "Auto-detect project type, service type, contract months",
    manual: "Tidak ada — fully automated saat accept",
    flow: "Titik konversi. Begitu klien Accept, sistem buat Contact (klien), Project (FIXED/RETAINER), Board kanban kosong, dan Workspace dari template service_type. Admin dapat notifikasi WA. Tidak perlu klik apapun.",
    nextHint: "Setelah ini langsung ke Board / Workspace untuk eksekusi.",
    badge: "Auto-project", link: "/clients",
  },
  {
    id: "board", label: "Board", sub: "Kanban", Icon: LayoutGrid,
    colorClass: "text-indigo-500", bgClass: "bg-indigo-500/10", borderClass: "border-indigo-500/30",
    trigger: "Auto-created saat proposal accepted",
    output: "Board kanban: To Do, In Progress, Review, Done",
    ai: "AI Agent bisa create/move/assign card lewat chat (agent mode)",
    manual: "Drag & drop card, assign, set due date, checklist",
    flow: "Eksekusi visual ala Trello. Card di Board sinkron 2-arah dengan row Workspace — ubah status di salah satu, pasangannya ikut update. AI Agent bisa diperintah lewat chat untuk bikin/pindah card.",
    nextHint: "Detail data per task → buka Workspace sheet.",
    badge: "AI Agent", link: "/board",
  },
  {
    id: "deliver", label: "Deliver", sub: "Workspace + Docs", Icon: Package,
    colorClass: "text-teal-500", bgClass: "bg-teal-500/10", borderClass: "border-teal-500/30",
    trigger: "Project aktif",
    output: "Spreadsheet workspace, dokumen (invoice, kontrak, proposal PDF)",
    ai: "Content generator: IG carousel, SEO article, TikTok, caption",
    manual: "Isi workspace, generate dokumen, kirim ke klien",
    flow: "Pengerjaan harian. Workspace = spreadsheet per project (multi-sheet untuk retainer per bulan). Tandai task milestone 'Invoice 30%/40%' jadi Done → modal auto-generate invoice. Dokumen lain (kontrak, surat) dibuat dari Document Generator pakai brand kit.",
    nextHint: "Project selesai → invoice final → masuk fase Retain (atau archive).",
    badge: null, link: "/workspace",
  },
  {
    id: "retain", label: "Retain", sub: "Followup + Invoice", Icon: RefreshCw,
    colorClass: "text-emerald-500", bgClass: "bg-emerald-500/10", borderClass: "border-emerald-500/30",
    trigger: "Project aktif + followup_enabled=true",
    output: "WA followup otomatis, invoice bulanan, upsell pipeline",
    ai: "AI Chat business partner untuk analisis retensi & upsell",
    manual: "Enable followup di Settings, input data finance",
    flow: "Pasca-deal. Untuk retainer: invoice tiap bulan, followup WA otomatis ke klien tidak aktif, AI Chat dipakai untuk analisis kesehatan akun & saran upsell. Loop balik ke Proposal kalau ada layanan tambahan.",
    nextHint: "Klien butuh layanan baru → balik ke tahap Proposal.",
    badge: "Auto-invoice", link: "/finance",
  },
];

const AI_FEATURES = [
  { name: "Chat", sub: "Business Partner", feature: "chat", color: "text-amber-500" },
  { name: "Agent", sub: "Task Executor", feature: "agent", color: "text-red-500" },
  { name: "Content", sub: "IG / SEO / TikTok", feature: "content", color: "text-blue-500" },
  { name: "Analysis", sub: "Lead Insights", feature: "analysis", color: "text-purple-500" },
];

function WorkflowMap() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [proxies, setProxies] = useState<{ id: string; name: string; model: string; feature: string | null; is_active: boolean }[]>([]);
  const [proxiesLoading, setProxiesLoading] = useState(true);
  const stage = PIPELINE_STAGES.find(s => s.id === expanded);

  useEffect(() => {
    apiFetch("/api/ai-proxies")
      .then(r => r.ok ? r.json() : [])
      .then(data => setProxies(data))
      .catch(() => {})
      .finally(() => setProxiesLoading(false));
  }, []);

  return (
    <div className="space-y-10">
      {/* Business Pipeline */}
      <div>
        <div className="mb-4">
          <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-50">Pipeline Bisnis</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Klik tiap node untuk lihat alur lengkap, trigger, output, dan aksi di tahap itu</p>
        </div>

        <div className="overflow-x-auto pb-2">
          <div className="flex items-start gap-1 min-w-max px-1">
            {PIPELINE_STAGES.map((s, i) => (
              <div key={s.id} className="flex items-start gap-1">
                <div className="flex flex-col items-center gap-2">
                  <button
                    onClick={() => setExpanded(expanded === s.id ? null : s.id)}
                    className={`relative flex flex-col items-center gap-1.5 px-3 py-3 rounded-2xl border-2 transition-all w-28 ${
                      expanded === s.id
                        ? `${s.bgClass} ${s.borderClass} shadow-lg scale-105`
                        : "bg-[var(--bg-surface)] border-[var(--border-default)] hover:shadow-md"
                    }`}
                  >
                    <s.Icon size={24} className={expanded === s.id ? s.colorClass : "text-neutral-500"} />
                    <span className={`text-xs font-bold ${expanded === s.id ? s.colorClass : "text-neutral-700 dark:text-neutral-300"}`}>{s.label}</span>
                    <span className="text-[10px] text-neutral-400 text-center leading-tight">{s.sub}</span>
                  </button>
                  {s.badge && (
                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${s.bgClass} ${s.colorClass} border ${s.borderClass} whitespace-nowrap`}>
                      <Zap size={8} className="inline -mt-0.5 mr-0.5" />{s.badge}
                    </span>
                  )}
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <div className="flex items-center mt-6 px-0.5">
                    <div className="w-5 h-0.5 bg-neutral-300 dark:bg-neutral-700" />
                    <div className="w-0 h-0 border-t-4 border-b-4 border-l-[6px] border-transparent border-l-neutral-300 dark:border-l-neutral-700" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {stage && (
          <div className={`mt-3 p-5 rounded-2xl border-2 ${stage.bgClass} ${stage.borderClass}`}>
            <div className="flex items-center gap-3 mb-4">
              <stage.Icon size={28} className={stage.colorClass} />
              <div>
                <h3 className={`font-bold text-base ${stage.colorClass}`}>{stage.label}</h3>
                <p className="text-xs text-neutral-500">{stage.sub}</p>
              </div>
              <a href={stage.link} className={`ml-auto text-xs font-semibold px-3 py-1.5 rounded-xl ${stage.bgClass} ${stage.colorClass} border ${stage.borderClass} hover:opacity-80 transition-opacity`}>
                Buka halaman →
              </a>
            </div>

            <div className="mb-4 p-4 rounded-xl bg-white/60 dark:bg-neutral-900/40 border border-[var(--border-subtle)]">
              <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">{stage.flow}</p>
              <p className="text-xs text-neutral-500 mt-2 font-medium">{stage.nextHint}</p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1">Trigger</p>
                <p className="text-neutral-700 dark:text-neutral-300">{stage.trigger}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1">Output</p>
                <p className="text-neutral-700 dark:text-neutral-300">{stage.output}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1">Fitur AI</p>
                <p className="text-neutral-700 dark:text-neutral-300">{stage.ai}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-neutral-400 mb-1">Aksi Manual</p>
                <p className="text-neutral-700 dark:text-neutral-300">{stage.manual}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* AI System Map */}
      <div>
        <div className="mb-4">
          <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-50">Sistem AI</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Tiap fitur bisa pakai model berbeda — routing otomatis lewat per-feature proxy yang dikonfigurasi di Settings</p>
        </div>

        <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-2xl p-6">
          <div className="flex flex-wrap gap-3 justify-center mb-2">
            {AI_FEATURES.map(f => (
              <div key={f.feature} className="flex flex-col items-center gap-0.5 px-5 py-3 rounded-2xl bg-neutral-100 dark:bg-neutral-800 border border-[var(--border-default)]">
                <span className={`text-sm font-bold ${f.color}`}>{f.name}</span>
                <span className="text-[10px] text-neutral-400">{f.sub}</span>
                <span className="text-[9px] font-mono text-neutral-400 mt-0.5">feature=&quot;{f.feature}&quot;</span>
              </div>
            ))}
          </div>

          <div className="flex justify-center">
            <div className="flex flex-col items-center">
              <div className="w-0.5 h-6 bg-neutral-300 dark:bg-neutral-700" />
              <div className="px-6 py-2.5 rounded-xl bg-brand-yellow/10 border-2 border-brand-yellow/40 text-center">
                <p className="text-xs font-bold text-brand-yellow font-mono">get_proxy_for_feature()</p>
                <p className="text-[10px] text-neutral-500 mt-0.5">feature-specific → fallback → default endpoint</p>
              </div>
              <div className="w-0.5 h-6 bg-neutral-300 dark:bg-neutral-700" />
            </div>
          </div>

          {proxiesLoading ? (
            <p className="text-center text-sm text-neutral-400 py-4">Memuat proxy...</p>
          ) : proxies.length === 0 ? (
            <p className="text-center text-sm text-neutral-400 py-4">Belum ada proxy. Tambah di Settings → AI Engine → AI Proxies.</p>
          ) : (
            <div className="flex flex-wrap gap-3 justify-center">
              {proxies.map(p => (
                <div key={p.id} className={`flex flex-col items-center gap-0.5 px-4 py-2.5 rounded-xl border border-[var(--border-default)] ${p.is_active ? "bg-emerald-500/10" : "bg-neutral-500/10"}`}>
                  <span className={`text-sm font-bold ${p.is_active ? "text-emerald-600 dark:text-emerald-400" : "text-neutral-500"}`}>{p.name}</span>
                  <span className="text-[10px] text-neutral-400">{p.model || "default"}</span>
                  {p.feature && <span className="text-[9px] font-mono text-neutral-400">{p.feature}</span>}
                </div>
              ))}
            </div>
          )}

          <p className="text-center text-[11px] text-neutral-400 mt-5">
            Tambah provider baru di <span className="font-semibold text-neutral-500 dark:text-neutral-300">Settings → AI Engine → AI Proxies</span>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function DocsPage() {
  const [view, setView] = useState<"docs" | "workflow">("docs");
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
      {/* Tab toggle */}
      <div className="flex items-center gap-2 mb-5">
        <button
          onClick={() => setView("docs")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
            view === "docs"
              ? "bg-brand-yellow/10 text-brand-yellow border border-brand-yellow/30"
              : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
          }`}
        >
          <Book size={14} />
          Dokumentasi
        </button>
        <button
          onClick={() => setView("workflow")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
            view === "workflow"
              ? "bg-brand-yellow/10 text-brand-yellow border border-brand-yellow/30"
              : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
          }`}
        >
          <GitBranch size={14} />
          Alur Kerja
        </button>
      </div>

      {view === "workflow" ? (
        <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-6 sm:p-8 overflow-y-auto h-[calc(100vh-180px)]">
          <WorkflowMap />
        </div>
      ) : (
      <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-180px)]">
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
                  <Check size={14} className="text-emerald-500 mt-0.5 shrink-0" />
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
      )}
    </div>
  );
}
