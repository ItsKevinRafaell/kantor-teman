# Codex Session Handoff - 2026-06-09

File ini adalah memori kerja terbaru untuk sesi Kantor Teman. Baca file ini di awal sesi Codex berikutnya sebelum mengubah kode.

## Konteks User

User ingin web Kantor Teman siap dipakai secara operasional, bukan sekadar tampilan. Bahasa UI harus Indonesia, ramah orang awam, dan workflow bisnis harus masuk akal untuk agency/UMKM.

User capek testing manual dan takut ada use case yang tidak ter-handle. Prioritas besar:

- Stabilitas semua modul utama.
- QA otomatis agar tidak selalu manual.
- Workflow bisnis yang jelas dari lead generation sampai invoice.
- Report/proposal mobile menarik dan tidak rusak.
- Board dan Workspace punya fungsi yang jelas dan tidak tumpang tindih.
- Role/user tim MVP karena tim akan memakai web.

## Prompt Awal User yang Menjadi Scope Besar

Masalah awal yang pernah user laporkan:

- Semua bahasa web harus Bahasa Indonesia yang ramah orang awam.
- Logic analitik perlu dijelaskan/diperbaiki: layanan paling diminati, distribusi pipeline, pola konversi.
- Board terlalu gelap/kurang aksen kuning; label card perlu warna soft, board jangan terlalu warna-warni.
- Drag and drop board tidak work.
- Checklist, komentar, log card board tidak work/tidak muncul dengan urutan terbaru di atas.
- Tombol simpan, arsip, hapus card tidak work.
- Card aktif yang diarsip harus hilang dari board aktif dan muncul saat mode arsip.
- Workspace terlalu hitam putih, perlu aksen kuning yang tidak sakit mata.
- Klik selesai di workspace harus ada konfirmasi, status otomatis jadi Done, dan board ikut sync.
- PIC/assignee harus search user yang register; kalau tidak ada akun lain tampilkan/tetapkan admin.
- Board dan workspace harus bisa search/filter by project name.
- Leads/prospek: tombol recalculate score perlu dibedakan dari filter; tombol `?` untuk jelaskan scoring.
- Layout filter/status leads sempat numpuk dan membingungkan.
- Peta tidak load baik.
- AI scrape perlu dijelaskan logic-nya.
- WA Blast harus generate report dan data report harus sesuai data AI scrape per client.
- Content generator hapus semua kecuali Artikel SEO, dan sidebar bug saat buka generator konten harus hilang.
- Arsip dokumen terlalu hitam putih dan create dokumen gagal.
- Semua CRUD di semua module perlu dipastikan bekerja.
- Invoice rincian layanan/layanan redundan, workflow bisnis perlu dipahami.
- Preview dokumen gagal karena `brand_kits.brand_name` missing.
- Dokumen harus generate PDF dengan ReportLab, resmi/profesional, editable, dan tujuan tiap dokumen jelas.
- Proposal, MoU, kontrak, invoice, arsip dokumen harus saling nyambung.
- Produk, kategori produk, template teks harus CRUD dan filter by kategori/status.
- Semua tabel perlu pagination.
- Brand kit tidak bisa add.
- AI Engine settings harus sederhana: base URL, API key, model, tanpa image generation/AI agent/caption sosmed.
- Backup data, seed, soft reset, nuclear reset harus benar; backup sejajar direktori project.

## Keputusan Workflow Bisnis dari Interview User

Workflow utama yang disepakati:

1. AI scrape / Maps scrape.
2. Lead tersimpan dalam batch.
3. Scoring otomatis, dan scoring bisa di-adjust manual.
4. Report dibuat per lead. Data report harus sesuai data lead/scrape masing-masing client.
5. WA Blast pilih batch, lalu filter by score/status, lalu kirim report.
6. Auto reply bot / auto lead gen adalah project terpisah nanti.
7. Jika lead tertarik: track reply WhatsApp, report opened, durasi baca report, dan status dari auto lead gen di masa depan.
8. Follow-up.
9. Proposal bisa dibuat dari lead, contact/client, atau halaman proposal.
10. Proposal PDF sebelum deal.
11. Proposal accepted/manual deal memicu client/project/board/workspace, invoice DP, MoU/kontrak, dan notifikasi admin.
12. MoU/kontrak/invoice setelah deal.
13. Invoice bulanan bisa otomatis berdasarkan project/retainer.
14. Project selesai jika invoice lunas dan admin klik selesai.
15. Dokumen perlu status workflow: approve/reject/sent/signed/archived dan nyambung ke arsip dokumen/klien.
16. Default global DP 50%, tapi bisa di-adjust.
17. Workspace menggantikan spreadsheet kerja lama.
18. Workspace harus berisi template SOP per layanan.
19. Board dan Workspace harus dibedakan:
    - Board = progress visual/Kanban, cepat melihat To Do/In Progress/Review/Done.
    - Workspace = spreadsheet operasional/SOP: PIC, deadline, output, link bukti, kriteria selesai, tracker per layanan.

Pendapat bisnis yang dicatat:

- Untuk cold lead, user ingin kirim report langsung sebelum jualan agar terasa care.
- Report harus menjadi lead magnet: memberi bukti analisis yang membuat UMKM tertarik.
- `report viewed` harus pakai Bahasa Indonesia.
- Open count report boleh naik setiap buka.
- Durasi baca penting; minimal/threshold engagement perlu dilanjutkan di project auto lead gen.
- Proposal bisa masuk arsip dokumen juga, tapi tetap ada halaman proposal publik/interaktif.
- Sistem notifikasi web dibutuhkan agar user tahu saat ada aksi otomatis.

## Pekerjaan yang Sudah Selesai Sebelum/di Sesi Ini

Catatan: worktree root sangat dirty dari banyak perubahan sebelumnya. Jangan reset/revert perubahan yang bukan milikmu.

Sudah ada/fixed dari iterasi sebelumnya:

- `.env` backend memakai DB lokal real: `DATABASE_URL=sqlite:///./leads.db`.
- `FRONTEND_URL=http://localhost:3002`.
- CORS untuk `localhost:3002` sudah dicek OK.
- Backend aktif di `127.0.0.1:8000`.
- Frontend production aktif di `localhost:3002`.
- Port lama `3000/3001` sudah tidak aktif setelah restart final.
- Board archive mode sudah mendukung `include_archived=true`.
- Board card attachments sudah ada dan smoke-tested.
- Archive document upload sudah ada dan smoke-tested.
- Workspace checkbox selesai mengubah status jadi Done dan sync linked board card ke Done.
- Public proposal endpoint menerima id atau slug.
- Generated documents bisa filter `lead_id` dan muncul di detail klien.
- Notifikasi dipindahkan ke TopBar dekat dark/light toggle.
- Document generator punya filter search, kategori/type, date range, asc/desc.
- Workspace service type endpoint label sudah benar, contoh `web_dev = Web Development`.

## Pekerjaan yang Diselesaikan di Sesi Ini

### 1. HCM / Role MVP

Backend:

- `backend/schemas/auth.py`
  - `UserCreate`
  - `UserAdminUpdate`
- `backend/schemas/__init__.py`
  - export schema user admin baru
- `backend/routers/auth.py`
  - `GET /api/users`
  - `POST /api/users`
  - `PUT /api/users/{user_id}`
  - `DELETE /api/users/{user_id}`
  - guard:
    - email unik
    - tidak bisa delete akun sendiri
    - tidak bisa delete admin terakhir
    - tidak bisa downgrade admin terakhir

Frontend:

- `frontend/src/app/settings/TeamTab.tsx`
  - UI create user, edit name/email/role, reset password, delete user.
- `frontend/src/app/settings/page.tsx`
  - tab baru `Tim & Role`.

Smoke:

- API HCM CRUD smoke PASS:
  - login admin
  - create test member
  - update test member
  - delete test member
  - cleanup test data

### 2. Report Fallback Tanpa AI Analysis Scrape

Masalah:

- Kalau `LeadAnalysis` tidak ada, backend mengembalikan `digital_analysis: null`.
- UI lama tetap memakai klaim terlalu keras seperti "SEO Lemah", "Maps Tidak Terlihat", dan pain points generic.
- Report bisa 500 karena import missing `get_monthly_search_volume`.

Perbaikan:

- `frontend/src/app/report/[slug]/page.tsx`
  - `buildFallbackPainPoints(report, city)` dari:
    - nama bisnis
    - kategori
    - kota
    - estimasi search volume
    - competitor/lead sejenis dari database
  - `parsePainPoints(report, city)` sekarang selalu menghasilkan poin relevan.
  - `ReportHero` kembali ditampilkan.
  - sticky header mobile diberi `min-w-0`, `overflow-hidden`, dan CTA bawah dibuat responsif agar tidak overflow.

- `frontend/src/components/report/ReportPainBox.tsx`
  - kalau tidak ada AI analysis: judul jadi `Area yang Perlu Dicek`.
  - copy menjelaskan bahwa data berasal dari data awal lead/scrape, bukan audit teknis final.

- `frontend/src/components/report/AuditScore.tsx`
  - kalau tidak ada AI analysis: badge jadi `SEO: Perlu Validasi`, `Maps: Cek Manual`, `Konversi: Perlu Dicek`.
  - tidak lagi klaim buruk secara absolut.

- `frontend/src/components/report/BeforeAfterComparison.tsx`
  - kalau tidak ada AI analysis: bagian "Kondisi Saat Ini" menjadi checklist validasi awal, bukan angka faktual palsu.

- `frontend/src/components/report/ReportHero.tsx`
  - copy pasar digital dilunakkan: estimasi pencarian dan peluang perlu ditangkap, bukan klaim semua pelanggan lari ke kompetitor.

- `frontend/src/components/report/ReportFOMOCloser.tsx`
  - competitor copy dikoreksi: "database lead mencatat bisnis sejenis", bukan "bisnis yang sedang membuka laporan ini".

- `backend/routers/proposals.py`
  - import `get_monthly_search_volume` dari `search_volume_data`.
  - import `send_fonnte_message` dari core dependency.
  - ini memperbaiki:
    - public report 500 `NameError: get_monthly_search_volume`.
    - proposal tracking open 500 `NameError: send_fonnte_message`.

### 3. Proposal Mobile Pricing Fix

Masalah:

- Screenshot Playwright menemukan proposal mobile menampilkan:
  - service price `Rp 1.000.000`
  - subtotal `Rp 0`
  - total final `Rp 0`
- Penyebab: `ProposalPricing` hanya memakai `base_price`, sedangkan proposal lama punya `base_price = null`.

Perbaikan:

- `frontend/src/components/proposal/ProposalPricing.tsx`
  - fallback subtotal:
    - `base_price`
    - atau `total_price`
    - atau sum `services_detail.price`
- E2E ditambah assert:
  - pricing section harus berisi `Rp 1.000.000`
  - tidak boleh berisi `Rp 0`.

### 4. Workspace Template SOP MVP

File:

- `backend/workspace_templates.py`

Template lama diganti menjadi template SOP berbahasa Indonesia yang lebih operasional.

Service types yang ada:

- `web_dev`
- `seo_gmaps`
- `sosmed`
- `maintenance`
- `web_dev_bulanan`
- `branding`
- `general`

Semua template punya konsep:

- Tahap
- Nama Task
- Status
- PIC
- Deadline
- Output / Link Bukti
- Kriteria Selesai
- Catatan
- Checkbox Selesai

SEO/GMB punya extra sheets:

- `Keyword Tracker`
- `Artikel Tracker`
- `Google Business Tracker`

Tujuan:

- Workspace benar-benar menggantikan spreadsheet kerja lama.
- Tim tahu task apa yang harus dikerjakan untuk tiap jenis layanan.
- Board tetap hanya visual progress, bukan tempat data detail.

### 5. SOP / Dokumentasi Internal Web

File:

- `frontend/src/components/docs/docsData.tsx`

Ditambahkan/diupdate:

- Section baru `SOP Workflow Bisnis`.
- Report docs menjelaskan fallback ketika AI analysis belum ada.
- Board docs menjelaskan Board = Kanban visual.
- Workspace docs menjelaskan Workspace = SOP spreadsheet operasional.
- Content generator docs difokuskan ke Artikel SEO.
- Settings docs menambahkan `Tim & Role`.
- Role docs menjadi `HCM MVP: Role & Akses`.
- Pipeline docs tidak lagi menonjolkan AI Agent.

### 6. QA Otomatis Playwright

Dependency:

- `@playwright/test` ditambahkan ke `frontend/package.json`.

Config:

- `frontend/playwright.config.ts`
  - pakai Chrome lokal (`channel: "chrome"`) agar tidak perlu download browser besar.
  - video off agar tidak butuh ffmpeg.
  - desktop smoke project.
  - mobile public project.

Tests:

- `frontend/tests/e2e/smoke.spec.ts`
  - login admin.
  - buka halaman utama:
    - dashboard
    - leads
    - clients
    - board
    - workspace
    - proposals
    - documents
    - document generator
    - content generator
    - settings team
    - master products/categories/templates
    - docs
  - cek tidak jatuh ke 404/token missing/fatal page.
  - ignore warning Next RSC fallback yang bukan error app.

- `frontend/tests/e2e/public-mobile.spec.ts`
  - mobile report:
    - report tampil
    - fallback tanpa AI analysis tampil
    - fakta pasar tampil
    - CTA WhatsApp tampil
    - tidak horizontal overflow
    - screenshot `frontend/qa-artifacts/report-mobile.png`
  - mobile proposal:
    - proposal tampil
    - pricing benar
    - CTA jelas
    - tidak horizontal overflow
    - screenshot `frontend/qa-artifacts/proposal-mobile.png`

Gitignore:

- `frontend/test-results/`
- `frontend/playwright-report/`
- `frontend/qa-artifacts/`

## Hasil Verifikasi Terakhir

Semua command ini sudah dijalankan dan PASS:

```bash
cd /home/kevin/kantorteman/backend && rtk pytest -q
# Result: 203 passed

cd /home/kevin/kantorteman/frontend && rtk npx tsc --noEmit --pretty false
# Result: TypeScript no errors

cd /home/kevin/kantorteman/frontend && rtk npm run build
# Result: build success

cd /home/kevin/kantorteman/frontend && rtk npx playwright test
# Result: PASS (3) FAIL (0)
```

Tambahan:

```bash
HCM CRUD smoke: PASS
CORS OPTIONS http://127.0.0.1:8000/api/notifications from http://localhost:3002 => 200
```

Service aktif terakhir:

- Backend: `127.0.0.1:8000`
- Frontend: `localhost:3002`
- Port `3000/3001`: tidak aktif
- Port `3004`: project lain, jangan dimatikan

Screenshot QA mobile:

- `frontend/qa-artifacts/report-mobile.png`
- `frontend/qa-artifacts/proposal-mobile.png`

## Update Codex 2026-06-10

Tugas awal sesi 2026-06-10 sudah dikerjakan:

- Handoff ini dibaca ulang.
- `git status --short` dicek. Root repo masih sangat dirty dan banyak file untracked dari sesi sebelumnya, termasuk worktree paralel. Tidak ada reset/revert.
- Baseline QA dijalankan ulang.
- E2E CRUD create-cleanup ditambah untuk risiko yang sebelumnya belum dijamin penuh.

File baru:

- `frontend/tests/e2e/crud-api.spec.ts`

Isi coverage baru:

- Master data:
  - create/update/delete kategori.
  - create/update/delete produk.
  - create/list/delete dynamic template `WA_BLAST`.
- Dokumen/invoice:
  - create lead QA.
  - create document template invoice.
  - generate PDF invoice via `/api/documents/generate`.
  - update workflow generated document ke `Dikirim` dan payment status `Lunas`.
  - cleanup archive/generated document/template/lead.
- Proposal:
  - create proposal lalu reject via public endpoint.
  - create proposal lalu accept via public endpoint.
  - assert accept membuat project aktif, board default, workspace berisi sheet/row.
  - cleanup project/contact/generated docs/proposal/lead sesuai kontrak aplikasi.
- Attachment:
  - create project.
  - create board card dan upload attachment.
  - assert attachment muncul di detail card.
  - upload workspace row attachment.
  - cleanup DB plus file fisik upload lokal di `backend/app/uploads`.
- Backup/reset guard:
  - backup tanpa auth harus 401.
  - reset soft/nuclear dengan password salah harus 403.
  - Tidak menjalankan backup besar atau reset sungguhan.

Catatan penting QA:

- Saat frontend dijalankan dengan `next dev`, Playwright sempat gagal karena first compile/hydration membuat form login dan halaman public masih loading sampai timeout.
- Setelah frontend dijalankan sesuai handoff lama dengan production server `npx next start -p 3002`, baseline Playwright PASS.
- Untuk QA stabil, jalankan build/start production sebelum `npm run qa:e2e`.

Verifikasi 2026-06-10:

```bash
cd /home/kevin/kantorteman/backend && rtk pytest -q
# Result: 203 passed

cd /home/kevin/kantorteman/frontend && rtk npx tsc --noEmit --pretty false
# Result: TypeScript no errors

cd /home/kevin/kantorteman/frontend && rtk npm run build
# Result: build success

cd /home/kevin/kantorteman/frontend && rtk npx playwright test tests/e2e/crud-api.spec.ts --project=chrome-desktop
# Result: PASS (5) FAIL (0)

cd /home/kevin/kantorteman/frontend && rtk npm run qa:e2e
# Result: PASS (8) FAIL (0)
```

Service aktif setelah sesi:

- Backend: `127.0.0.1:8000`
- Frontend production: `localhost:3002`

Risiko sisa setelah update ini:

- E2E CRUD baru masih API-level, belum klik UI form satu per satu untuk produk/kategori/template/dokumen/proposal.
- Reset/backup positif belum dites otomatis karena berisiko menghapus/menghasilkan file besar di data aktif.
- Seed/demo/reset positive path tetap harus dites di environment disposable.
- Masih ada konteks `CODEX_AFTER_CLAUDE_HANDOFF.md` tentang worktree paralel dan isu contact-id vs lead-id yang belum diintegrasikan di root.

## Indikator Web "Sudah Bisa Dipakai"

Tidak ada software yang bisa dijamin 0 bug tanpa test suite yang terus diperluas. Tapi indikator objektif saat ini:

- Backend unit/integration test 203 pass.
- Frontend typecheck pass.
- Frontend production build pass.
- E2E smoke modul utama pass.
- Report mobile pass dan tidak overflow.
- Proposal mobile pass, CTA jelas, pricing benar.
- HCM CRUD API smoke pass.
- Backend/frontend service berjalan di port yang benar.

Ini sudah jauh lebih baik daripada testing manual murni.

## Risiko / Hal yang Belum Dijamin Penuh

E2E saat ini masih smoke, belum exhaustive CRUD untuk semua modul. Belum otomatis mencoba semua kombinasi create/update/delete di:

- produk
- kategori
- template
- dokumen semua tipe
- invoice semua status
- semua flow accept/reject proposal
- semua attachment path
- semua reset/backup/seed mode

Untuk tahap berikutnya, perlu tambah E2E CRUD terfokus per modul dengan create-cleanup data test.

Worktree root masih sangat dirty dari banyak perubahan sebelumnya. Jangan jalankan:

- `git reset --hard`
- `git checkout --`
- command destructive lain

kecuali user eksplisit meminta.

## File Penting yang Berubah/Baru

Baru:

- `CODEX_SESSION_HANDOFF_2026-06-09.md`
- `frontend/playwright.config.ts`
- `frontend/tests/e2e/smoke.spec.ts`
- `frontend/tests/e2e/public-mobile.spec.ts`
- `frontend/src/app/settings/TeamTab.tsx`

Berubah penting:

- `.gitignore`
- `backend/routers/auth.py`
- `backend/schemas/auth.py`
- `backend/schemas/__init__.py`
- `backend/routers/proposals.py`
- `backend/workspace_templates.py`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/app/settings/page.tsx`
- `frontend/src/app/report/[slug]/page.tsx`
- `frontend/src/components/report/*`
- `frontend/src/components/proposal/ProposalPricing.tsx`
- `frontend/src/components/docs/docsData.tsx`

## Cara Menjalankan Ulang QA

```bash
cd /home/kevin/kantorteman/backend
rtk pytest -q

cd /home/kevin/kantorteman/frontend
rtk npx tsc --noEmit --pretty false
rtk npm run build
rtk npm run qa:e2e
```

Kalau perlu restart service:

```bash
# cek port
rtk ss -ltnp | rtk grep -E ':3000|:3001|:3002|:8000' || true

# backend
cd /home/kevin/kantorteman/backend
rtk bash -lc 'setsid -f python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > /tmp/kantorteman-backend.log 2>&1'

# frontend production
cd /home/kevin/kantorteman/frontend
rtk bash -lc 'setsid -f npx next start -p 3002 > /tmp/kantorteman-frontend.log 2>&1'
```

## Prompt Siap Pakai untuk Sesi Besok

```text
Kita lanjut dari sesi Kantor Teman tanggal 2026-06-09.

Pertama, baca file ini:
/home/kevin/kantorteman/CODEX_SESSION_HANDOFF_2026-06-09.md

Konteks penting:
- User ingin web Kantor Teman siap dipakai operasional, bukan cuma UI.
- Workflow bisnis sudah disepakati: AI scrape/Maps scrape → scoring → report per lead → WA blast filter batch/score → track report viewed/durasi → follow-up → proposal → closing → project → board/workspace → invoice/dokumen → selesai/arsip.
- Board = Kanban visual progress.
- Workspace = spreadsheet SOP detail per layanan, menggantikan spreadsheet lama.
- Content generator difokuskan hanya Artikel SEO.
- HCM/role MVP sudah dibuat di Settings → Tim & Role.
- Report tanpa AI analysis scrape sudah dibuat fallback dari data lead/kategori/kota/search volume/lead sejenis, dan copy-nya harus jujur, tidak overclaim.
- Proposal mobile pricing bug `Rp 0` sudah diperbaiki.
- QA otomatis Playwright sudah ditambahkan dan terakhir PASS.

Sebelumnya masalah besar yang harus diingat:
- User capek testing manual dan takut use case tidak ter-handle.
- Banyak bug lama: CORS, data kosong, login, board drag/drop/archive/delete/checklist/comment/log, proposal 500, document generator, attachment, filter leads, workspace sync, report/proposal mobile, role tim.
- Jangan reset/revert worktree karena repo sedang dirty dari banyak perubahan.
- Semua command shell harus pakai prefix `rtk`.

Status terakhir:
- Backend aktif di 127.0.0.1:8000.
- Frontend aktif di localhost:3002.
- Port 3000/3001 tidak aktif; port 3004 project lain jangan dimatikan.
- Verifikasi terakhir:
  - backend pytest: 203 passed
  - frontend tsc: no errors
  - frontend build: success
  - Playwright e2e: PASS (3) FAIL (0)
  - HCM CRUD smoke: PASS

Tugas awal sesi besok:
1. Jangan langsung refactor besar. Baca handoff dan cek git status.
2. Jalankan QA ulang cepat:
   cd backend && rtk pytest -q
   cd frontend && rtk npx tsc --noEmit --pretty false
   cd frontend && rtk npm run qa:e2e
3. Lanjutkan dari risiko yang belum dijamin penuh: tambah E2E CRUD create-cleanup untuk modul produk, kategori, template, dokumen, invoice, proposal accept/reject, board/workspace attachment, dan backup/reset guard.
4. Kalau menemukan bug dari QA, fix dengan clean architecture, jangan patch asal.
5. Tetap jelaskan ke saya dalam Bahasa Indonesia yang jelas: apa yang dites, apa yang pass, apa bug nyata, dan apa risiko sisa.
```
