# FIX A2 — Inject Chart PNG ke Laporan Klien (evidence.items)

**Branch:** `feat/nara-e2e-fixes`
**Report contoh:** MLS — report_id `442c0bd8`, public slug `laporan-bulanan-seo-google-map-90d3d6a`.

## Masalah
Chart tren GSC (`chart-mls-clicks.png`, `chart-mls-position.png`, 880x506) berhasil di-generate
oleh `gsc_chart_gen.py` **TAPI nyangkut lokal** di `/root/.hermes/shared/outputs/`. Laporan klien
dikirim dengan `evidence` **kosong**, jadi klien cuma lihat angka teks tanpa grafik.

Akar masalah: script generator `gsc_to_erp_report.py` mengirim `"evidence": {}` ke
`POST /api/reports/generate`. Chart PNG tidak pernah di-upload ke server.

## Alur yang benar (sudah diimplementasi)
1. `gsc_chart_gen.py` bikin `chart-<slug>-<kind>.png` dari JSON GSC (`--gen-charts` opsional untuk regen).
2. Untuk tiap chart PNG: `POST /api/reports/attachments` (multipart, field `file`) → balikin `file_url`
   (mis. `/uploads/reports/<uuid>/<uuid>.png`).
3. Susun `evidence.items = [{label, url:file_url, file_name, file_type:"image/png", source:"gsc_chart"}]`.
   Bentuk ini **persis** yang dibaca `client_report_service._render_evidence`.
4. `POST /api/reports/generate` dengan `evidence={"items":[...]}` → snapshot menyimpan `evidence_json`.
5. `render_report_html` → `_render_evidence` → tiap item image → `<img src="{FRONTEND_URL}{file_url}">`
   inline di section **Bukti Pengerjaan** (tampil di public report + PDF).

## File yang diubah
- `scripts/reports/gsc_to_erp_report.py` (vendored copy dari `/root/.hermes/shared/outputs/`):
  - `+_post_multipart()` — upload file via urllib (tanpa `requests`).
  - `+run_chart_gen()` / `+find_chart_pngs()` / `+build_chart_evidence_items()`.
  - `main()`: setelah login, upload chart PNG → inject ke `payload["evidence"]["items"]` sebelum generate.
  - Flag baru: `--gen-charts` (regen chart dulu), `--no-charts` (matikan injeksi, perilaku lama).
  - Verifikasi: cetak `evidence.items` yang balik dari snapshot.
- `scripts/reports/gsc_chart_gen.py` (vendored copy, tidak diubah logic-nya).

> Catatan: kedua script generator sebelumnya hidup HANYA di `/root/.hermes/shared/outputs/`
> (di luar repo, tidak ke-track git). Copy resmi sekarang di `scripts/reports/` supaya versinya
> ke-commit. Backend (`client_report_service.py`, `routers/reports.py`) **tidak perlu diubah** —
> path render `evidence.items` → inline `<img>` sudah benar.

## Yang sudah dites (tanpa nyentuh prod)
- `find_chart_pngs("mls")` → menemukan 2 PNG.
- `build_chart_evidence_items` (upload di-mock) → item shape `{label,url,file_name,file_type,source}` valid.
- `client_report_service._render_evidence(payload)` (fungsi backend ASLI, di-exec terisolasi) →
  menghasilkan **2 inline `<img>`** dengan absolute URL. Chart benar-benar ke-render.
- `gsc_to_erp_report.py --client mls --dry-run` → payload valid, log injeksi chart benar.

## Yang MASIH perlu diverifikasi live (butuh akses prod — sengaja TIDAK dijalankan)
1. `POST /api/reports/attachments` beneran nerima PNG 880x506 (< 5MB, ext .png allowed → OK) dan
   balikin `file_url` yang bisa diakses publik.
2. Regenerate report MLS: `python3 scripts/reports/gsc_to_erp_report.py --client mls --gen-charts`
   lalu buka public report → pastikan 2 grafik muncul di section "Bukti Pengerjaan" + PDF.
3. `FRONTEND_URL` / `frontend_url` setting di prod benar, supaya `_absolute_url` menghasilkan URL
   gambar yang bisa dibuka klien (bukan relative broken).
