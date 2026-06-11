# CODEX SESSION HANDOFF - 2026-06-10

Gunakan file ini di sesi Codex berikutnya. Baca file ini setelah
`CODEX_SESSION_HANDOFF_2026-06-09.md`.

## Prinsip Kerja User

- User ingin web Kantor Teman siap operasional, bukan hanya UI.
- Jangan reset/revert worktree. Repo memang dirty dari banyak perubahan lintas sesi.
- Semua command shell harus pakai prefix `rtk`.
- Jangan matikan port 3004 karena itu project lain.
- Bahasa UI dan penjelasan harus jelas dalam Bahasa Indonesia untuk workflow agency/UMKM.
- User capek testing manual, jadi setiap perubahan besar harus ditutup dengan QA otomatis.

## Diskusi Produk Hari Ini

Topik utama: laporan bulanan dan laporan akhir proyek.

Masalah user:
- Laporan bulanan lama terlalu generik.
- Untuk SEO, laporan profesional harus memuat data Google Search Console, komparasi bulan ini vs bulan lalu, insight, update pekerjaan, dan rekomendasi.
- Untuk maintenance, laporan harus memuat bukti backup, update plugin/theme/core, security/site health, form/WA/checkout test, incident, dan rekomendasi.
- User bingung karena dokumen bisa dibuat dari beberapa tempat. Navigasi perlu diperjelas.
- User bertanya beda generate dari tanpa target, lead, klien/contact, dan proyek.

Keputusan produk:
- Semua hal yang berhubungan dengan generate file/link tetap masuk area yang sama: **Dokumen & Laporan**.
- Di dalam area itu flow dibedakan jelas:
  - **Dokumen Resmi**: invoice, kwitansi, kontrak, MoU, surat penawaran, proposal PDF.
  - **Proposal**: proposal sales interaktif dengan accept/reject dan tracking.
  - **Laporan Klien**: laporan bulanan/selesai proyek/performa layanan.
  - **Audit Lead**: laporan pre-sales untuk prospek hasil scrape/lead.
  - **Arsip**: file manager folder/subfolder untuk dokumen/link/file.
- Proposal boleh tetap punya menu/shortcut lama, tapi juga masuk mental model "Dokumen & Laporan".
- Output laporan klien harus **PDF + link publik tracked**.
- Fase pertama tidak menunggu OAuth GSC/GA4/GBP/Meta. Manual input/CSV-ready dulu, tapi data Workspace, Board, attachment/bukti, dan PageSpeed otomatis wajib.

Definisi target:
- **Tanpa target**: laporan/dokumen internal umum, tidak auto-pull data klien.
- **Lead**: pre-sales/prospect, pakai data lead/kategori/lokasi/scoring/report tracking.
- **Klien/Contact**: account-level document/report, pakai identitas dan histori klien.
- **Proyek**: operational report, pakai workspace, board, attachment, invoice/dokumen, service type, dan periode.

## Implementasi Hari Ini

Backend:
- Tambah model `ReportSnapshot` di `backend/models/document.py`.
- Export `ReportSnapshot` di `backend/models/__init__.py` dan `backend/app/core/dependencies.py`.
- Tambah migrasi `report_snapshots` di `backend/migrate.py` untuk SQLite dan MySQL.
- Tambah service baru `backend/app/services/client_report_service.py`.
  - Build payload laporan dari target.
  - Auto ambil Workspace task summary, status, evidence/link/attachment.
  - Auto ambil Board card summary.
  - Manual metric per service type.
  - Auto PageSpeed via PageSpeed Insights API jika URL tersedia.
  - Render HTML laporan.
  - Render PDF.
  - Create `GeneratedDocument`.
  - Auto archive ke file manager via `archive_generated_document`.
  - Create public slug.
  - Track open count, first/last viewed, max duration.
- Tambah router `backend/routers/reports.py`.
  - `GET /api/reports/config`
  - `GET /api/reports/draft`
  - `GET /api/reports`
  - `GET /api/reports/{report_id}`
  - `POST /api/reports/generate`
  - `GET /api/reports/public/{slug}`
  - `POST /api/reports/public/{slug}/duration`
  - `GET /api/reports/public/{slug}/download`
- Include router reports di `backend/main.py`.
- Reset guard diperbarui:
  - `backend/routers/settings.py`
  - `backend/reset_data.py`
  - `backend/reset_full.py`
  - `ReportSnapshot` dihapus sebelum `GeneratedDocument` saat reset.

Frontend:
- Sidebar group "DOKUMEN" diubah menjadi **DOKUMEN & LAPORAN**.
- Menu:
  - `/documents` label **Dokumen & Laporan**.
  - `/documents/generator` label **Dokumen Resmi**.
  - `/documents/reports` label **Laporan Klien**.
- `/documents` sekarang jadi hub flow di atas file manager:
  - Buat Dokumen Resmi
  - Buat Proposal
  - Buat Laporan Klien
  - Audit Lead
  - Arsip tetap di bawahnya.
- Tambah Report Builder:
  - `frontend/src/app/documents/reports/page.tsx`
  - `frontend/src/app/documents/reports/page.content.tsx`
  - Target: project, lead, contact, empty.
  - Report type: monthly, completion, internal, lead_audit.
  - Metric manual per service type:
    - `seo_gmaps`
    - `maintenance`
    - `sosmed`
    - `web_dev`
    - `web_dev_bulanan`
    - `branding`
    - `general`
  - Toggle Auto PageSpeed.
  - Toggle public tracked link.
  - Daftar laporan terbaru dengan copy link dan download PDF.
- Tambah public client report page:
  - `frontend/src/app/client-report/[slug]/page.tsx`
  - Fetch public payload.
  - Track duration pakai beacon/fetch.
  - Download PDF lewat endpoint public report.
- Workspace detail:
  - Tombol lama "Generate Laporan" diganti menjadi link **Buat Laporan** ke `/documents/reports?target_type=project&project_id=...&report_type=monthly&month=...`.
  - Ini membuat flow laporan konsisten dengan hub Dokumen & Laporan.
- `/reports` sekarang redirect ke `/documents/reports`.
- `/documents/generator` copy diubah dari "Document Generator" menjadi **Dokumen Resmi**.
- Generated document list sekarang mengenali tipe **Laporan Klien** jika `template_name/display_filename` berisi laporan.
- E2E smoke expectation diperbarui agar menerima label baru `Dokumen Resmi`.

## Riset Laporan Per Layanan

Sumber rujukan resmi yang dipakai saat diskusi:
- Google Search Console Performance: clicks, impressions, CTR, average position.
- Google Business Profile performance: views/searches/actions, calls, directions, website clicks.
- GBP Performance API: daily/monthly performance report.
- GA4 Data API schema untuk metric/dimension reporting.
- PageSpeed Insights API untuk performance metrics.
- Meta/Instagram Insights untuk reach, engagement/interactions, followers/media metrics.
- WordPress backup/update/site health untuk maintenance report.

Template data laporan per layanan:
- **SEO & Google Maps**
  - GSC clicks, impressions, CTR, average position.
  - Komparasi bulan ini vs bulan lalu.
  - Top queries/pages nanti bisa manual/CSV.
  - GBP views, calls, directions, website clicks.
  - Artikel publish, keyword tracker, optimasi halaman, backlink/citation, next steps.
- **Maintenance Website**
  - Backup date/status/link/size.
  - Core/plugin/theme updates.
  - Security/site health.
  - Uptime, incidents, form/WA/checkout test.
- **Sosmed**
  - Posts, reach, engagement, follower delta, top content.
- **Web Development**
  - Pages/features done, QA status, PageSpeed/mobile check, handover link, blocker/change request.
- **Branding**
  - Deliverables, revision round, approval status, final asset link.
- **General**
  - Completed tasks, blocker, next steps, evidence links.

## QA Terakhir

Setelah implementasi:
- `cd backend && rtk pytest -q`
  - PASS: **205 passed**
- `cd frontend && rtk npx tsc --noEmit --pretty false`
  - PASS: no TypeScript errors
- `cd frontend && rtk npm run build`
  - PASS: build success
- `cd frontend && rtk npm run qa:e2e`
  - PASS: **10 passed**

Catatan QA:
- Playwright sempat gagal 3 test karena server 3002/8000 yang aktif masih stale.
- Backend port 8000 dan frontend port 3002 sudah direstart dari kode terbaru.
- Setelah restart, public mobile report/proposal pass.
- Sisa 1 failure adalah smoke test masih mencari label lama "Document Generator"; expectation test sudah diupdate ke `Dokumen Resmi`.
- Rerun final e2e: 10 passed.

Server aktif saat handoff:
- Backend: `http://127.0.0.1:8000`
- Frontend: `http://localhost:3002`
- Jangan matikan port 3004.

## Bug Nyata yang Ditemukan dan Difix

- Public report PDF awalnya jika memakai endpoint `/api/documents/{id}/download` akan butuh login. Difix dengan endpoint public:
  - `GET /api/reports/public/{slug}/download`
- Reset data belum membersihkan laporan baru. Difix dengan delete `ReportSnapshot` di reset admin dan reset scripts.
- E2E smoke test stale terhadap label lama. Difix expectation test.

## Risiko Sisa

Belum dikerjakan:
- OAuth/API connector real untuk GSC, GA4, Google Business Profile, Meta/Instagram.
- CSV parser/import khusus untuk GSC/Meta belum dibuat. Fase sekarang input manual/API-ready.
- Scheduler auto-generate laporan bulanan belum dibuat.
- Belum ada dashboard khusus "laporan yang belum dikirim bulan ini".
- Public client report sudah fungsional, tapi belum ada branding/visual polish setingkat proposal public page.
- Permission detail untuk siapa yang boleh melihat/mengirim laporan masih mengikuti auth umum.

Rekomendasi next session:
1. Baca file ini dan handoff 2026-06-09.
2. Cek git status, jangan revert.
3. Jalankan quick QA:
   - `cd backend && rtk pytest -q tests/test_client_reports.py`
   - `cd frontend && rtk npx tsc --noEmit --pretty false`
4. Jika lanjut fitur laporan:
   - Tambah CSV import GSC sederhana.
   - Tambah halaman daftar "Laporan bulan ini" per project/retainer.
   - Polish public report visual dan copy Bahasa Indonesia.
   - Tambah E2E khusus `/documents/reports` UI create report.

## File Baru Penting

- `backend/app/services/client_report_service.py`
- `backend/routers/reports.py`
- `backend/tests/test_client_reports.py`
- `frontend/src/app/documents/reports/page.tsx`
- `frontend/src/app/documents/reports/page.content.tsx`
- `frontend/src/app/client-report/[slug]/page.tsx`
- `CODEX_SESSION_HANDOFF_2026-06-10.md`

## File Existing yang Tersentuh Hari Ini

- `backend/main.py`
- `backend/migrate.py`
- `backend/models/document.py`
- `backend/models/__init__.py`
- `backend/app/core/dependencies.py`
- `backend/routers/settings.py`
- `backend/reset_data.py`
- `backend/reset_full.py`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/app/documents/page.content.tsx`
- `frontend/src/app/documents/generator/page.tsx`
- `frontend/src/app/documents/generator/new/page.tsx`
- `frontend/src/app/workspace/[project_id]/page.tsx`
- `frontend/src/app/reports/page.tsx`
- `frontend/tests/e2e/smoke.spec.ts`

## Pesan untuk Codex Berikutnya

User kemungkinan akan berkata "lanjut dari sesi kemarin" atau "baca handoff".
Langsung baca file ini, jangan asumsi dari memori model.
Jangan tanya ulang hal yang sudah diputuskan di atas kecuali user ingin revisi arah produk.

## Update Sesi Lokal 2026-06-10 Malam

Konteks terbaru dari diskusi user:
- User minta **local saja**, jangan pakai `tmux`, jangan tunnel Cloudflare. Percobaan `tmux`/`cloudflared` dibatalkan.
- Server dev manual yang dipakai:
  - Frontend: `http://127.0.0.1:3000/login/`
  - Backend: `http://127.0.0.1:8000`
- Login lokal sempat gagal karena mismatch origin:
  - frontend dibuka dari `127.0.0.1:3000`
  - API sebelumnya ke `localhost:8000`
  - backend CORS belum allow `127.0.0.1:3000`
- Fix yang sudah dilakukan:
  - `frontend/.env.local`: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
  - `backend/.env`: `CORS_ORIGIN` allow `localhost:3000/3001/3002` dan `127.0.0.1:3000/3001/3002`
  - `frontend/next.config.js`: dev CSP tambah `unsafe-eval`, allow local `localhost`/`127.0.0.1` untuk `connect-src` dan `img-src`
  - `frontend/src/app/login/page.tsx`: tombol login hanya disabled saat loading; form pakai `method="post"`; submit baca `FormData`; URL lama yang bocor `?email=...&password=...` dibersihkan via `history.replaceState`
- Verifikasi terakhir:
  - CORS preflight `OPTIONS /api/auth/login` dari `Origin: http://127.0.0.1:3000` = `200 OK`
  - `GET /api/brand-kit/public` = `200 OK`
  - `POST /api/auth/login` dengan `admin@kantorteman.com/admin123` = `200 OK`
  - CSP header sudah mengandung `script-src 'self' 'unsafe-inline' 'unsafe-eval'`

Diskusi role:
- Role masih sederhana: `admin` dan `member`.
- Member = staff operasional, bukan viewer-only.
- Member bisa akses menu operasional: Dashboard, Panduan, Klien, Board, Workspace, Prospek, Proposal, Analitik Pesan, Kalender Konten, Generator Konten, Dokumen & Laporan, Dokumen Resmi, Laporan Klien.
- Admin-only di sidebar: Keuangan, Campaign & Kuota, Arsip Internal, Katalog Produk, Kategori Produk, Template Teks, Brand Kit, Antrean Tugas, Pengaturan.
- Backend tetap pakai action-level guard `require_admin` untuk settings, finance, user management, master data, brand kit, delete sensitif, create/update/delete project, scrape/import besar, campaign create/delete, credential vault, dll.
- Rekomendasi production: pertimbangkan role granular `admin`, `manager`, `operator/member`, `viewer/client`.

Diskusi laporan klien:
- User ingin dokumen/laporan komparasi yang field-nya sama tetapi tampil **2 kolom Before / After**.
- User juga ingin bisa memilih periode pembanding: before dari tanggal-sampai tanggal, after dari tanggal-sampai tanggal.
- Makna field "Dari tanggal" / "Sampai tanggal" di Laporan Klien: periode data yang dilaporkan. Idealnya dipakai untuk filter aktivitas Workspace/Board/evidence yang masuk ke dokumen dan untuk label periode di PDF/public report.
- Untuk aktivitas periode, sumber paling defensible:
  - Workspace rows/cells berdasarkan tanggal task (`value_date`, kolom tanggal/due date bila ada) atau fallback `updated_at/created_at`
  - Board card/activity berdasarkan `due_date`, `updated_at`, `created_at`, dan `BoardCardActivity.created_at`
  - Evidence/attachment berdasarkan `uploaded_at`
- Belum selesai implementasi before/after UI/backend. Kalau lanjut, tambahkan struktur `comparison_periods` dan render tabel PDF/public report dengan kolom `Before`, `After`, `Delta`.
