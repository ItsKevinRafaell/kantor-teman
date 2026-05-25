# Backlog — User Review (2026-05-25)

## Priority: High (Core Flow Broken)

- [x] **Scraper tidak bisa jalan** — UX fix: empty state message saat 0 hasil
- [x] **Proposal 404** — fix: rewrite /r/ /p/ ke backend + middleware bypass auth
- [x] **Batch → Model** — batch_name di ScrapeHistory, pagination, search, lead_count
- [x] **Maps scraper → Leads table link** — klik batch row → navigate ke contacts?batch=
- [x] **Field teks chat AI tidak bisa diketik** — fix trailing slash /chat/ di ClientLayout

## Priority: Medium (UX & Workflow)

- [x] **Toast/modal konfirmasi** — sudah ada di 15 pages, pattern OK
- [x] **WA reply → auto status "Replied"** — Fonnte webhook endpoint added
- [x] **Closed vs Jadi Klien** — renamed Closed → Closed/Lost, Closed/Client tetap
- [x] **Tambah proyek ikut paket** — product selector di project create modal
- [x] **Pagination semua tabel** — Pagination component + leads, products, templates, proposals
- [x] **Scraper filter by date** — date_from/date_to di backend + date picker UI
- [x] **Leads tabel horizontal scroll** — min-w-[1100px] force scroll
- [x] **Status leads diperbaiki** — renamed Closed → Closed/Lost
- [x] **Durasi buka proposal di-fix** — track/open + ping setiap 10s di proposal page
- [x] **Auto-deduct clarification** — renamed "Catat Pengeluaran Bulan Ini" + tooltip
- [x] **Kredensial kategori dinamis** — sudah ada (autocomplete + add new + rename)
- [x] **Template teks — flow & efek diperjelas** — type hints, variable chips clickable, usage context
- [x] **Dokumentasi variabel template teks** — clickable chips + per-type usage info
- [x] **Trello rules — admin only** — role check on card move to Done/Revisi/Selesai
- [x] **Sidebar menu toggle** — "Atur Menu" button, localStorage-based show/hide
- [ ] **SEO ↔ Image Generator integration** — DEFERRED: requires content-generator refactor

## Priority: Low (Polish)

- [x] **Proposal timeline "Proyek Selesai" terlalu kecil** — text-[9px] → text-xs
- [x] **Modal search WA blast** — 2-col grid, compact padding

---

*Remaining: SEO ↔ Image Generator integration (next session)*
