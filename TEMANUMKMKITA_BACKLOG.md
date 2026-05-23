# Backlog — temanumkmkita.com

Website company profile + blog CMS untuk Teman UMKM Kita. Full Next.js 14, animasi premium tapi tasteful, SEO-first.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 App Router, TypeScript, Tailwind CSS |
| Animasi | Framer Motion |
| Backend | FastAPI + SQLAlchemy (hosting 2, Python) |
| Database | MySQL (hosting 2) |
| Deployment | Vercel (frontend) + LiteSpeed Passenger WSGI (backend) |
| Domain | temanumkmkita.com |

Repo terpisah dari kantorteman. Dua Vercel project terpisah.

---

## Brand & Design System

### Warna
```
--accent:        #f5a700   /* Optimism Yellow — primary */
--brand-dark:    #242423   /* Dark Charcoal — text, contrast */
--bg-canvas:     #fcfaf7   /* Pure Snow — background */
```

Konsisten dengan kantorteman.my.id.

### Tipografi
- Display/heading: bold, besar, weight 700–900
- Body: regular, readable, weight 400–500
- Tone: percaya diri, membumi, Bahasa Indonesia

### Animasi (Framer Motion)
| Elemen | Animasi |
|---|---|
| Hero text | Word-by-word reveal on load |
| Hero background | Animated gradient mesh / floating orbs kuning |
| Navbar | Blur backdrop, hide on scroll down, show on scroll up |
| Stats bar | Count-up saat masuk viewport |
| Service cards | 3D tilt on hover + shine sweep |
| Section entries | Staggered fade + slide-up (tidak semua sekaligus) |
| CTA button | Magnetic hover (tombol ikut cursor subtle) |
| Page transition | Smooth fade antar halaman |
| Blog cards | Scale + shadow on hover |
| Testimonial | Carousel autoplay smooth |

Referensi visual: vercel.com, raycast.com — clean, dark-accent, premium feel.

---

## Halaman (13 total)

| Route | Halaman | Prioritas |
|---|---|---|
| `/` | Homepage | P0 |
| `/tentang-kami` | About Us | P1 |
| `/layanan` | Overview semua layanan | P0 |
| `/layanan/web-development` | Web Dev + harga | P0 |
| `/layanan/seo-google-maps` | SEO + harga | P0 |
| `/layanan/kelola-sosial-media` | Sosmed + harga | P0 |
| `/layanan/maintenance-website` | Maintenance + harga | P1 |
| `/layanan/desain-logo` | Logo + harga | P1 |
| `/portofolio` | Case studies klien | P1 |
| `/kontak` | Form + info kontak | P0 |
| `/blog` | List artikel (SSG+ISR) | P2 |
| `/blog/[slug]` | Detail artikel (SSG+ISR) | P2 |
| `/404` | Custom not found | P2 |

---

## Struktur Tiap Halaman

### Homepage `/`
1. Navbar (sticky, blur on scroll)
2. Hero — headline besar + subheadline + CTA "Konsultasi Gratis"
3. Stats bar — X klien aktif, X proyek selesai, X layanan
4. Problem section — "Bisnis bagus, tapi susah ditemukan online?"
5. Layanan overview — 5 card animasi dengan link ke halaman masing-masing
6. Cara kerja — 4 langkah (Konsultasi → DP → Eksekusi → Go-Live)
7. Testimonial — PT MLS (SEO), PT MHK (Maintenance + Website)
8. CTA banner — "Mulai sekarang, konsultasi gratis"
9. Footer

### Halaman Layanan (template sama, konten berbeda)
1. Hero section — nama layanan + headline masalah yang diselesaikan
2. Apa yang kamu dapat — benefit list dengan ikon
3. Paket & Harga — tabel Starter / Pro / Expert (dari seed data)
4. Proses pengerjaan — timeline visual
5. FAQ — 4–5 pertanyaan umum
6. CTA — "Pilih paket ini, hubungi kami"

### About Us `/tentang-kami`
1. Hero — "Siapa Teman UMKM Kita?"
2. Cerita bisnis — narasi singkat
3. Nilai-nilai — 3 prinsip kerja
4. Tim (opsional untuk fase awal)
5. CTA

### Portofolio `/portofolio`
1. Hero
2. Filter kategori layanan
3. Grid case study card — nama klien, layanan, hasil
4. CTA

### Kontak `/kontak`
1. Hero
2. Form — nama, WA, layanan yang diminati, pesan
3. Info kontak — WA langsung, email
4. Peta / lokasi (opsional)

### Blog `/blog`
1. Hero
2. Featured article
3. Grid artikel
4. Pagination / infinite scroll

### Blog Detail `/blog/[slug]`
1. Hero — judul + meta (tanggal, kategori)
2. Konten artikel (rich text / MDX)
3. Related articles
4. CTA sidebar / bottom

---

## Database Schema (MySQL hosting 2)

```sql
CREATE TABLE articles (
  id          VARCHAR(36) PRIMARY KEY,
  title       VARCHAR(500) NOT NULL,
  slug        VARCHAR(500) UNIQUE NOT NULL,
  excerpt     TEXT,
  content     LONGTEXT NOT NULL,
  cover_image VARCHAR(500),
  category    VARCHAR(255),
  tags        TEXT DEFAULT '[]',     -- JSON array
  status      VARCHAR(50) DEFAULT 'draft',  -- draft / published
  published_at VARCHAR(255),
  created_at  VARCHAR(255) NOT NULL,
  updated_at  VARCHAR(255)
);

CREATE TABLE article_categories (
  id    VARCHAR(36) PRIMARY KEY,
  name  VARCHAR(255) NOT NULL,
  slug  VARCHAR(255) UNIQUE NOT NULL
);
```

---

## API Endpoints (FastAPI hosting 2)

| Method | Route | Fungsi |
|---|---|---|
| GET | `/api/articles` | List artikel published, support ?category=, ?limit= |
| GET | `/api/articles/{slug}` | Detail artikel by slug |
| POST | `/api/articles` | Buat artikel baru (dari kantorteman Content Generator) |
| PUT | `/api/articles/{id}` | Update artikel |
| DELETE | `/api/articles/{id}` | Hapus artikel |
| GET | `/api/categories` | List kategori blog |

Auth: Bearer token (same secret key seperti kantorteman).

---

## Integrasi dengan Kantorteman

### 1. Data Produk (Build Time)
- temanumkmkita fetch `GET api.kantorteman.my.id/api/public/products` saat build (SSG)
- Data produk/harga otomatis sinkron tanpa deploy ulang jika pakai ISR

**Perlu dibuat di kantorteman:**
```
GET /api/public/products     → semua produk aktif + kategori
GET /api/public/categories   → semua kategori aktif
```
Endpoint publik, no auth.

### 2. Publish Artikel dari Content Generator
- Di kantorteman, Content Generator tambah tombol **"Publish ke temanumkmkita"**
- Kirim POST ke `api.temanumkmkita.com/api/articles` dengan Bearer token
- Status artikel langsung `published`

---

## Backlog Tasks

### Fase 1 — Foundation
- [ ] Init repo `temanumkmkita` — Next.js 14 App Router + TypeScript + Tailwind
- [ ] Setup Framer Motion
- [ ] Setup design tokens (warna, font, spacing) di globals.css
- [ ] Layout komponen: Navbar, Footer
- [ ] Setup FastAPI backend di hosting 2
- [ ] Init MySQL + jalankan migrations
- [ ] Deploy Vercel + connect domain temanumkmkita.com

### Fase 2 — Core Pages (P0)
- [ ] Homepage — semua sections
- [ ] `/layanan` overview
- [ ] `/layanan/web-development`
- [ ] `/layanan/seo-google-maps`
- [ ] `/layanan/kelola-sosial-media`
- [ ] `/kontak`

### Fase 3 — Secondary Pages (P1)
- [ ] `/layanan/maintenance-website`
- [ ] `/layanan/desain-logo`
- [ ] `/tentang-kami`
- [ ] `/portofolio`

### Fase 4 — Blog (P2)
- [ ] `/blog` list (SSG+ISR)
- [ ] `/blog/[slug]` detail (SSG+ISR)
- [ ] Sitemap.xml + robots.txt
- [ ] JSON-LD structured data per artikel
- [ ] Open Graph image per artikel

### Fase 5 — Integrasi (P2)
- [ ] `GET /api/public/products` di kantorteman backend
- [ ] Tombol "Publish ke Website" di Content Generator kantorteman
- [ ] ISR revalidation trigger saat artikel baru dipublish

---

## Catatan Copywriting

Tiap halaman layanan harus punya:
- **Hook**: satu kalimat masalah yang biasa dirasakan UMKM
- **Empati**: tunjukkan kamu paham situasinya
- **Solusi**: layanan ini menyelesaikan masalah itu dengan cara ini
- **Bukti**: hasil nyata / paket yang jelas
- **CTA**: satu aksi yang jelas

Tone: hangat, percaya diri, tidak korporat, Bahasa Indonesia.

---

## Kontak Bisnis (untuk footer/halaman kontak)
- WhatsApp: +62 895-0192-5395
- Website: temanumkmkita.com
