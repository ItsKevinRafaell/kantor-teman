# Kantor Teman — Marketing Automation User Flow

## Gambaran Umum Sistem

Kantor Teman adalah CRM + Marketing Automation untuk agensi digital lokal. Sistem ini mengotomasi seluruh pipeline penjualan dari scraping leads → blast WA → audit report → scoring → closing.

---

## User Flow Marketing (End-to-End)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  1. SCRAPE  │ ──▶ │ 2. BLAST WA  │ ──▶ │ 3. REPORT AUDIT │ ──▶ │  4. CLOSING  │
│  Google Maps│     │  + Link Report│     │  (Halaman Publik)│     │  via WA/Call │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
```

### 1. Scrape Leads dari Google Maps
- Admin mencari bisnis lokal berdasarkan kategori + kota
- Data masuk ke tabel `leads` dengan status `Scraped`
- Data: nama bisnis, nomor WA, alamat, kategori (product_interest)

### 2. Blast WhatsApp dengan Link Report
- Admin membuat campaign blast, pilih template, pilih filter leads
- Sistem otomatis generate proposal + slug untuk setiap lead
- Template WA dikirim via Fonnte API, berisi link report: `{{proposal_link}}`
- Status lead berubah: `Scraped` → `BLASTED`

### 3. Lead Membuka Link Report
- Lead klik link → masuk halaman `/report/{slug}`
- Halaman report menampilkan:
  - **Pain Box** — masalah kritis bisnis mereka
  - **Search Volume** — fakta berapa orang cari jasa mereka di Google
  - **Before vs After** — perbandingan kondisi saat ini vs setelah optimasi
  - **ROI Slider** — kalkulator proyeksi omzet interaktif
  - **FAQ Accordion** — jawaban keberatan umum
  - **FOMO Timer** — countdown 24 jam harga diskon (dikunci di database)
  - **Competitor Count** — berapa kompetitor sejenis di kota mereka
  - **CTA WhatsApp** — tombol chat langsung ke admin
- Sistem tracking otomatis:
  - `first_viewed_at` dicatat (timer mulai)
  - Lead score bertambah berdasarkan aktivitas
  - Status lead: `BLASTED` → `REPORT_VIEWED` → `HOT_PROSPECT`

### 4. Closing
- Admin lihat dashboard CRM, leads diurutkan by score (tertinggi di atas)
- Ghost Viewer (buka 5x+ dalam 48 jam) ditandai badge merah
- Admin gunakan "Laci Balasan Cepat WA" untuk handle objection
- Deal closed → status `CLOSED`

---

## Template WhatsApp yang Tersedia

### Template Tipe: `WA_BLAST`

#### 1. Blast SEO Promo
```
Halo {{business_name}},

Saya baru saja menjalankan audit digital gratis untuk bisnis Anda dan hasilnya cukup mengkhawatirkan.

❌ Website Anda tidak muncul di halaman utama Google Maps
❌ Kecepatan loading di bawah standar (calon pelanggan kabur)
❌ Kompetitor Anda sudah lebih dulu teroptimasi

Saya sudah buatkan laporan lengkap + kalkulator proyeksi omzet di sini:
👉 {{proposal_link}}

⚠️ Harga spesial di laporan ini hanya berlaku 24 jam karena slot optimasi wilayah Anda terbatas bulan ini.

Bisa saya jelaskan lebih detail, Pak?
```

#### 2. Blast Web Dev Promo
```
Halo {{business_name}},

Tim kami baru saja menganalisis performa digital bisnis Anda dan menemukan beberapa masalah serius yang membuat calon pelanggan lari ke kompetitor setiap harinya.

🔴 Website belum mobile-friendly (70% pengunjung dari HP)
🔴 Tidak ada sistem konversi pengunjung jadi pelanggan
🔴 Kalah saing di pencarian lokal Google

Laporan audit lengkap + solusi sudah saya siapkan di sini:
👉 {{proposal_link}}

⏰ Penawaran harga khusus hanya berlaku 24 jam. Setelah itu kembali ke harga normal.

Ada waktu 5 menit untuk saya jelaskan, Pak?
```

#### 3. Template Blast Web DEV (Soft Approach)
```
Halo {{business_name}},

Perkenalkan, saya dari tim Kantor Teman. Kami fokus membantu bisnis lokal seperti Anda untuk mendominasi pencarian Google di wilayah operasional Anda.

Kami sudah buatkan analisis gratis untuk bisnis Anda:
👉 {{proposal_link}}

Di dalam laporan tersebut Anda bisa lihat:
✅ Skor performa website Anda saat ini
✅ Berapa calon pelanggan yang hilang setiap bulan
✅ Kalkulator proyeksi omzet jika diperbaiki

⚠️ Slot optimasi untuk wilayah Anda bulan ini sangat terbatas. Cek sekarang sebelum diambil kompetitor.

Silakan dibuka, Pak. Gratis tanpa komitmen.
```

### Template Tipe: `FOLLOW_UP` (Default di Kode)

#### Follow-Up: Belum Buka Link
```
Halo Pak, saya notice laporan audit digital untuk {business_name} belum dibuka. 
Laporan ini ada timer 24 jam untuk harga spesial. Mau saya kirim ulang linknya sekarang?
```

### Template Default Chat WA Manual (dari Dashboard)
```
Halo {{business_name}}, saya baru saja menjalankan audit digital gratis untuk bisnis Anda 
dan hasilnya cukup mengkhawatirkan — ada beberapa masalah kritis yang membuat calon pelanggan 
Anda lari ke kompetitor setiap harinya.

Saya sudah buatkan laporan lengkapnya di sini:
{{proposal_link}}

⚠️ Laporan ini hanya berlaku 24 jam karena slot optimasi wilayah Anda terbatas. 
Setelah itu harga kembali normal.

Bisa saya jelaskan lebih detail, Pak?
```

---

## Variabel Template yang Tersedia

| Variabel | Deskripsi | Contoh Output |
|----------|-----------|---------------|
| `{{business_name}}` | Nama bisnis lead | PT Kaliman Karya Jaya |
| `{{proposal_link}}` | Link report audit publik | http://localhost:3000/report/pt-kaliman-karya-jaya |
| `{{client_name}}` | Alias dari business_name | PT Kaliman Karya Jaya |
| `{{product_name}}` | Kategori produk/jasa lead | SEO |

---

## Lead Scoring System

| Aktivitas | Poin | Kondisi |
|-----------|------|---------|
| LINK_CLICKED | +30 | Sekali saja (first human interaction) |
| ROI_SLIDER_VIEWED | +25 | Scroll sampai area slider |
| SHARE_PARTNER_CLICKED | +20 | Klik tombol share ke partner |
| IS_MOBILE | +10 | Buka dari HP (bukan desktop) |

**Maksimal skor: 100**

### Anti-Bot Filter
Skor TIDAK dihitung jika request dari:
- WhatsApp preview bot
- Facebook external hit
- Googlebot / Twitterbot / Telegrambot
- Admin yang sedang login (JWT valid)

### Ghost Viewer Detection
- Lead yang buka link >= 5x dalam 48 jam → ditandai `🔥 GHOST VIEWER - HIGH INTENT`
- Muncul di dashboard dengan highlight merah + animate-pulse

---

## Outreach Lifecycle State Machine (Auto, tiap 1 jam)

| Rule | Kondisi | Status Baru |
|------|---------|-------------|
| No Click Follow-up | Status `BLASTED` + 48 jam tanpa klik | `FOLLOWUP_QUEUE` |
| Viewed but Stagnant | Status `REPORT_VIEWED`/`HOT_PROSPECT` + 24 jam tanpa kontak | `WARM_STAGNANT` |

---

## Halaman Report vs Proposal

| Aspek | Report (`/report/{slug}`) | Proposal (`/proposal/{id}`) |
|-------|---------------------------|------------------------------|
| Tujuan | Audit gratis, trigger urgency | Penawaran jasa spesifik |
| Target | Lead baru (di-blast) | Lead yang sudah tertarik |
| Konten | Pain Box, ROI Slider, FOMO Timer | Daftar layanan + harga |
| Link dikirim via | Template WA Blast | Manual oleh admin |
| Auth | Publik (tanpa login) | Publik (tanpa login) |
| Timer | 24 jam dari first view | Tidak ada |

---

## Cara Membuat Proposal dengan Layanan Spesifik

1. Buka halaman **Buku Klien** (`/clients`)
2. Klik tombol "Buat Proposal" pada klien yang diinginkan
3. Di modal form, pilih layanan dari **Katalog Produk** (multi-select checkbox)
   - Hanya produk yang relevan yang perlu dicentang
   - Tidak harus semua produk — pilih sesuai kebutuhan klien
4. Klik "Buat Proposal"
5. Sistem otomatis:
   - Generate slug unik dari nama bisnis
   - Set harga diskon 15% off (berlaku 24 jam)
   - Simpan layanan yang dipilih ke `services_detail`
   - Generate FAQ default

---

## Produk/Layanan yang Tersedia (Database)

### Kategori: SEO
| Produk | Harga |
|--------|-------|
| SEO Premium | Rp 3.000.000 |
| Setup Google Maps Bisnis & Optimasi Ulasan | Rp 500.000 |
| Optimasi SEO Lokal (On-Page + Off-Page) | Rp 2.500.000 |
| Riset Kata Kunci Intent Pembeli | Rp 750.000 |

### Kategori: Web Development
| Produk | Harga |
|--------|-------|
| Pembuatan Website Company Profile | Rp 3.500.000 |
| Pembuatan Landing Page Konversi Tinggi | Rp 2.000.000 |
| Integrasi WhatsApp Chat Bot Otomatis | Rp 1.500.000 |

### Kategori: Social Media Management
| Produk | Harga |
|--------|-------|
| Kelola Instagram Bisnis (30 Konten/Bulan) | Rp 2.000.000 |
| Kelola TikTok Bisnis (20 Video/Bulan) | Rp 2.500.000 |
| Desain Feed & Story Template Branding | Rp 1.000.000 |

---

## Environment Variables

### Backend (`.env`)
```
GOOGLE_API_KEY=...
JWT_SECRET=kantor-teman-secret-change-in-prod
SECRET_ENCRYPTION_KEY=...
FRONTEND_URL=http://localhost:3000
FONNTE_TOKEN=...
```

### Frontend (`.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ADMIN_WA=6285156843788
```
