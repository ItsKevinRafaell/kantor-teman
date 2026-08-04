# Blueprint A — Report Bulanan Klien Komprehensif (ERP kantorteman)

Status dokumen: SPEC (belum eksekusi). Dibuat 2026-08-04.
Ruang lingkup: web ERP `api.kantorteman.my.id`, source lokal `/home/kevin/kantorteman`.

## 0. TL;DR keputusan
- Report tinggal DI ERP (bukan Hermes generate sendiri). ERP = tempat render + arsip.
- Pengisian data BEBAS: boleh ERP auto-tarik (GSC/pagespeed) ATAU agent (rafi) input via kt.py.
  Agent paham datanya + bisa generate grafik/screenshot + dokumen pendukung.
- Target: halaman report jadi laporan KOMPREHENSIF setara isi lengkap ERP.

## 1. Temuan audit codebase (apa yang SUDAH ada)
Dibaca dari `backend/routers/reports.py` + `backend/app/services/client_report_service.py`.

SUDAH ADA (jangan bangun ulang):
- Model `ReportSnapshot` + `GeneratedDocument` (arsip PDF per report).
- Endpoint lengkap:
  - `GET  /api/reports/config`         -> label tipe & service
  - `GET  /api/reports/draft`          -> preview payload sebelum generate
  - `GET  /api/reports`                -> list (filter project_id/lead_id/type)
  - `GET  /api/reports/{id}`           -> detail
  - `POST /api/reports/generate`       -> bikin snapshot (metrics/evidence/narrative + run_pagespeed)
  - `GET  /api/reports/public/{slug}`  -> versi publik (share ke klien)
  - `POST /api/reports/attachments`    -> upload screenshot/bukti (jpg/png/webp/pdf, max 5MB)
  - `POST /api/reports/public/{slug}/duration` -> tracking durasi baca klien
  - `GET  /api/reports/public/{slug}/download`  -> download PDF
- **PDF renderer SUDAH ADA**: `app/services/pdf_renderer.render_pdf_from_html`.
- Data sources yang udah dirakit ke report: workspace sheets, board cards, target project, GSC (via run_pagespeed), manual metrics per service_type.
- Brand context per klien (`build_brand_context`) untuk header/logo.

Artinya: fondasi report 80% jadi. Yang kurang bukan "bangun report", tapi LENGKAPI CELAH.

## 2. Celah yang perlu ditutup (scope kerja sebenarnya)

### A. Kelengkapan konten report (komprehensif)
UPDATE AUDIT: template report SUDAH render banyak section di client_report_service.py
(_render_comparison_section "Komparasi Performa", "Target Bulan Depan", _render_service_section
"Performa SEO & Google Maps" + "Maintenance/Backup/Keamanan", dll). Section2 nampilin placeholder
"belum diisi" kalau kosong. Jadi "komprehensif" secara STRUKTUR sudah ada — masalah M07 MLS kosong
itu karena DATA belum diinput, bukan template hilang. Aksi A jadi: (1) input data lengkap ke report
MLS 0377c416 M07 sbg uji nyata, (2) baru identifikasi section yang beneran masih kurang.
Kandidat section yang mesti dipastikan ada & terisi:
- [ ] Ringkasan eksekutif (narrative.summary) — auto-draft dari metrics kalau kosong.
- [ ] Metrik SEO (GSC: klik, impresi, posisi rata2, query teratas) — dari run_pagespeed/GSC.
- [ ] PageSpeed / Core Web Vitals sebelum-sesudah.
- [ ] Daftar pekerjaan bulan ini (dari board cards / workspace) — sudah ada, pastikan tampil rapi.
- [ ] Bukti/screenshot (evidence.items) — sudah ada channel upload-nya.
- [ ] Grafik tren (impresi/klik per bulan) — perlu chart. Opsi: render chart jadi PNG di sisi
      agent lalu upload sebagai evidence, ATAU generate SVG inline di template HTML report.
- [ ] Rekomendasi bulan depan (narrative.next_steps).
Aksi: baca penuh `build_report_payload` + template HTML report, buat checklist section mana sudah
dirender dan mana belum, tambal yang kurang di template + service.

### B. Alur pengisian data oleh AGENT (kt.py)
Kevin izinkan agent input sendiri. Butuh command kt.py (wrapper CRM) yang manggil endpoint di atas:
- `kt.py reportdraft <project_id> <month>`   -> GET /api/reports/draft (lihat yang kekumpul)
- `kt.py reportupload <file>`                -> POST /api/reports/attachments -> balikin file_url
- `kt.py reportgen <project_id> <month> --metrics ... --evidence ... --narrative ...`
                                             -> POST /api/reports/generate
- `kt.py reports [--project <id>]`           -> GET /api/reports (list + public_url)
Catatan: sebagian command ini mungkin SUDAH ada di kt.py (memory menyebut reportdata/genreport/
reportgen/reports). Aksi pertama: cek kt.py aktual di VPS, samakan nama, jangan bikin duplikat.

### C. Kirim email report ke klien
UPDATE AUDIT: SMTP + kirim PDF via email SUDAH ADA di `routers/documents.py` (~baris 1530-1578):
smtplib + MIMEMultipart + attach PDF, config dari Settings (smtp_host/port/user/pass/from),
handle port 465 SSL vs 587 starttls. Jadi TIDAK perlu tulis util SMTP dari nol.
Aksi (kecil): tambah `POST /api/reports/{id}/email` body {to, cc?, subject?, message?} yang:
- ambil PDF dari GeneratedDocument milik report (pola download_public_report sudah ada),
- reuse blok SMTP dari documents.py (ekstrak jadi util bersama `email_service.py` biar DRY),
- kt.py: `kt.py reportmail <report_id> <to>`.
Guardrail: JANGAN auto-kirim tanpa perintah (draft dulu, kirim manual).

### D. Grafik / chart (untuk "komprehensif")
Dua opsi, pilih yang paling murah dirawat:
1. Agent-side: agent generate chart PNG (matplotlib/plotly) -> upload via reportupload ->
   masuk sebagai evidence. Paling fleksibel, ga nyentuh backend render.  <-- REKOMENDASI awal.
2. Server-side: template HTML report render chart (chart.js saat HTML, atau SVG statis untuk PDF).
   Lebih rapi tapi nyentuh pdf_renderer (WeasyPrint tidak eksekusi JS -> harus SVG/PNG statis).

## 3. Urutan eksekusi (kalau sudah di-ACC)
1. Baca `build_report_payload` penuh + template HTML report -> checklist section (celah A).
2. Cek kt.py aktual di VPS -> petakan command report yang sudah ada vs perlu ditambah (celah B).
3. Tambah endpoint email + util SMTP (celah C).
4. Putuskan strategi chart (celah D) — default agent-side PNG.
5. Uji end-to-end dengan project MLS aktif 0377c416 bulan M07 (yang sekarang masih kosong).

## 4. Guardrail
- JANGAN otomasi report/invoice tanpa perintah eksplisit. Draft & tampilkan, Kevin kirim manual.
- JANGAN hardcode angka klien di memory/soul — selalu tarik live dari ERP.
- Test pakai data real project MLS 0377c416, bukan dummy.
