# Production Deploy Guide: Kantorteman

## Sebelum Upload

Backup tiga hal ini dari shared hosting:

- database MySQL melalui export panel hosting
- folder `uploads/`
- file `.env`

Jangan upload database lokal, folder `uploads/`, atau `.env` dari laptop ke server.

## Upload Backend

Upload isi `backend-production-hardening.zip` ke folder backend aplikasi dengan struktur folder tetap dipertahankan. Paket ini hanya berisi source code dan dependency list yang berubah.

Setelah upload, jalankan dari folder backend:

```bash
pip install -r requirements.txt
python migrate.py
```

Lalu restart aplikasi Passenger dari panel shared hosting.

Jangan jalankan `seed.py` atau `reset_data.py` pada production. Dua script tersebut hanya untuk database kosong di development atau staging.

## Environment Backend

Pastikan `.env` production memiliki nilai yang benar:

```dotenv
JWT_SECRET="random-secret-panjang"
SECRET_ENCRYPTION_KEY="fernet-key-yang-sudah-dipakai"
DATABASE_URL="mysql+pymysql://user:password@localhost/database"
FRONTEND_URL="https://kantorteman.my.id"
CORS_ORIGIN="https://kantorteman.my.id"
ENABLE_BACKGROUND_SCHEDULER="false"
FONNTE_WEBHOOK_SECRET=""
```

Catatan:

- Jangan mengganti `SECRET_ENCRYPTION_KEY` jika sudah ada data brankas terenkripsi.
- Isi `FONNTE_WEBHOOK_SECRET` hanya jika provider webhook dapat mengirim header `x-fonnte-webhook-secret`. Jika diisi, callback tanpa header tersebut ditolak.
- Di shared hosting Passenger/cPanel, biarkan `ENABLE_BACKGROUND_SCHEDULER="false"` supaya setiap worker web tidak menjalankan scheduler sendiri. Jalankan scheduler hanya dari worker/process terpisah.
- `--probe` dulu (cetak rencana flag, tidak start job). Kalau `.env` web master=false (snapshot prod), `--probe` saja = no-op. First-enable AMAN = `--safe-first` (alias `--enable followup`, process-local, **tidak tulis `.env`**) supaya worker terpisah bisa start tanpa nyalain master di Passenger. `--dry-run` berhenti sebelum BlockingScheduler. Blast ditolak kecuali `--allow-blast` (ACC Kevin). Billing by-tanggal **jangan** first-enable — invoice retainer = turunan report final (`SAFE_FIRST_ENABLE=followup`). `--safe-first --enable billing` di-REFUSE (exit 2).
- Contoh (setelah Kevin nulis "deploy"): `python3 scripts/run_scheduler_worker.py --safe-first --dry-run` lalu tanpa `--dry-run`. Jangan `--enable blast` tanpa ACC. Jangan `--enable billing` kecuali Kevin override PLAN-report-invoice.
- Snapshot env prod 30 Agu 2026 (SSH read-only `qqwtlphb`): `.env` hanya `ENABLE_BACKGROUND_SCHEDULER=false`, sub-flag absen, `flags.py` + worker **belum** di server, `stderr.log` 0 APScheduler. Tes pengunci: `tests/test_scheduler_prod_snapshot.py` + `tests/test_scheduler_enable_cli.py`. Jangan nyalain master di `.env` Passenger.
- API key provider dapat diatur dari menu admin setelah deploy.

### Runbook aktivasi worker scheduler (setelah Kevin tulis "deploy")

Prasyarat: `feat/raka-scheduler-job-specs-main` di-merge ke `main` (owner raka, `FLEET_MAIN_OWNER=1`) lalu deploy standar via `deploy.sh` — bukan copy file serpihan. Worker `scripts/run_scheduler_worker.py` melakukan `import main`, dan `main.py` baru meng-import `app/schedulers/flags.py`, jadi server wajib menerima `main.py` + `app/schedulers/flags.py` + `scripts/run_scheduler_worker.py` + `scripts/__init__.py` sekaligus (deploy berbasis git menjamin itu).

Urutan eksekusi di server (path: `/home/qqwtlphb/backend`):

1. Verifikasi pasca-deploy, tanpa efek:
   `python3 scripts/run_scheduler_worker.py --probe` → `master=false`, `will_start=false`, 0 job, exit 0 (`.env` web tak tersentuh).
2. Rencana first-enable aman (followup saja):
   `flock -n /tmp/kt-sched.lock python3 scripts/run_scheduler_worker.py --safe-first --dry-run` → `job_ids=followups`; dry-run tidak import `main`, tidak sentuh DB.
3. REHEARSAL LOKAL (bukti 3 Sep 2026, main `f97cd47`): dry-run → plan JSON benar (master ON, `job_ids=followups`, blast/billing/lifecycle OFF, 0 sentuh DB); `--once` ke salinan SQLite → `[SCHEDULER] once: run followups ...` + `once selesai`, exit 0; gerbang blast: env `ENABLE_BLAST_SCHEDULER=true` tanpa `--allow-blast` → `REFUSE` exit 3 (dan `--safe-first` menetralkan env kotor: blast di-set false in-process).
   PITFALL lokal: `.env` dev berisi `SECRET_ENCRYPTION_KEY` placeholder → `import main` gagal (`Fernet key must be 32 url-safe base64...`). Rehearsal `--once`/`--safe-first` (yang import `main`) butuh key Fernet valid via env (`SECRET_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")`). PROD tidak terpengaruh (key prod valid, API hidup).
4. Aktif via crontab mode `--once` (job jalan 1x lalu exit — tidak ada daemon yang bisa dibunuh cron/timeout sebelum fire pertama, karena APScheduler fire pertama = now+interval):
   `20 * * * * flock -n /tmp/kt-sched.lock python3 /home/qqwtlphb/backend/scripts/run_scheduler_worker.py --safe-first --once >> /home/qqwtlphb/backend/scheduler-worker.log 2>&1`
   → cadence hourly (JOB_TRIGGERS: `followups` interval 1 jam); offset menit bebas, `flock -n` mencegah overlap.
5. Bukti jalan (SELESAI kalau semua ada): log `scheduler-worker.log` berisi `[SCHEDULER] once: run followups ...` + `once selesai`, dan e2e: 1 lead masuk sequence → followup terjadwal terproses.
6. Level berikutnya (masing-masing butuh ACC eksplisit Kevin, jangan sekalian di-crontab): blast hanya via daemon `--allow-blast` (interval 1 menit), JANGAN lewat `--once`; billing crontab harian sesuai JOB_TRIGGERS (`subscription-deductions` 00:05, `project-billing-invoices` 00:15) hanya setelah Kevin override PLAN-report-invoice.

Rollback scheduler = hapus 1 baris crontab; `.env` web dan Passenger tidak disentuh.

## Verifikasi Setelah Restart

1. Login dengan akun admin yang sudah ada.
2. Buka dashboard dan pastikan data proyek tampil.
3. Buka `Keuangan`, pastikan saldo dan runway dapat dibaca admin.
4. Arsipkan satu lead test dan pulihkan kembali.
5. Buat satu folder arsip, tambahkan subfolder, lalu simpan link dokumen.
6. Generate satu invoice dan cek preview PDF sebelum download.
7. Kirim satu pesan WhatsApp test sebelum menjalankan blast batch.

## Rollback

Jika aplikasi gagal start setelah deploy:

1. restore source code versi sebelumnya
2. restore database hanya jika migrasi menyebabkan masalah data
3. restart Passenger

Migrasi saat ini hanya menambahkan kolom lead sales dan opt-out. Tidak ada reset data.

## Runbook Go-Live Scheduler Prod (butuh "deploy" dari Kevin — JANGAN jalan sendiri)

Status 31 Agu 2026 23:xx WIB (re-verified): API prod 200. Root-cause 500 sore itu =
`schemas/board.py` stale tanpa `BoardCardChecklistUpdate` (hotfix 22:11:50 + restart 22:12:56).
Worker + `flags.py` BELUM di server. E2E lokal PASS:
`backend/venv/bin/python scripts/e2e_lifecycle_local.py` (lead WA_Terkirim + proposal 72h →
"Follow Up" + audit NO_CLICK_FOLLOWUP, sqlite throwaway). Suite scheduler lokal 31 passed
(`test_scheduler_flags` + `test_scheduler_enable_cli` + `test_scheduler_prod_snapshot` +
`test_billing_invoice_idempotency`). Branch kanonis: `feat/raka-e2e-scheduler-enable`
(merge `feat/raka-scheduler-job-specs-main` 31 Agu 23:xx, commit `8d99a09`).

**Jalur kanonis = crontab `--once` + `--safe-first` (lihat section di atas).**
`.env` Passenger TIDAK disentuh. Master `ENABLE_BACKGROUND_SCHEDULER` tetap `false`.

**Eksekutor one-shot (direkomendasikan saat Kevin menulis "deploy"):**
`bash scripts/scheduler_golive.sh <status|check|deploy-code|activate|verify|rollback>`.
Membungkus langkah 2-6 runbook persis (git-pull via `deploy.sh` → health → `--probe` →
crontab `--once` idempotent → 1x run manual via flock → bukti log). Perintah yang
mengubah state prod (`deploy-code`/`activate`/`rollback`) MENOLAK jalan (exit 3)
tanpa env `KT_SCHED_GOLIVE_ACK=deploy`. `status`/`verify`/`check` read-only penuh.

**DITOLAK sebagai first-enable (bukti teknis, jangan nurut biar keliatan cepat):**
- Flip master ON di `.env` web = tiap LSAPI worker spawn APScheduler sendiri (alasan dimatiin 12 Jun).
- `nohup` BlockingScheduler di shared hosting: fire pertama APScheduler = now+interval; process
  yang dibunuh timeout/cron sebelum itu fire 0x. `--once` + `flock -n` adalah jawaban.
- Rsync HANYA `flags.py` + worker TANPA `main.py` baru: `main.py` repo import `app.schedulers.flags`
  → ImportError → API DOWN. Untuk first-enable TIDAK PERLU sentuh `main.py` sama sekali —
  lihat § Jalur Upload First-Enable di bawah (worker `--once` import `main` LIVE, bukan repo).
- ~~git pull setelah merge ke `main`~~ **DITOLAK (bukti layout 1 Sep 2026 malam):** git toplevel
  di server = `/home/qqwtlphb/backend` (live root) TAPI tracked tree ber-prefix `backend/` →
  `git pull` hanya update `~/backend/backend/*` (folder nested), file live TIDAK ter-update
  (live `main.py` bahkan untracked, md5 `a392e43…`, Aug 20). `deploy.sh` live juga masih
  panggil `python migrate.py` — `python` TIDAK ada di jailshell → `set -e` mati sebelum
  restart. `scheduler_golive.sh deploy-code` sekarang MENOLAK otomatis saat layout nested
  terdeteksi (exit 1); override `KT_SCHED_GOLIVE_FORCE_DEPLOY_CODE=1` hanya setelah
  `deploy.sh.NEW` v2 (flock+mysqldump+python3+health-rollback, draft nara 20 Agu) di-review
  Kevin + dites + sync live root.
- `--all` deploy script TIDAK meng-upload `app/schedulers/` dan `scripts/`.
- Nyalain billing/blast sekalian first-enable. Billing = mutasi uang. Blast = WA massal.
  Masing-masing butuh ACC Kevin terpisah. Blast butuh `--allow-blast` (exit 3 tanpa itu).

### Jalur Upload First-Enable (kanonis — TANPA restart Passenger)

File yang perlu masuk server (base64 via `deploy_kantorteman.sh --file ... --no-restart`,
verifikasi tiap file dengan `grep -c` marker di server — "Deploy complete" TIDAK membuktikan
apa-apa, lihat pitfall 0):

1. `backend/app/schedulers/flags.py` → `~/backend/app/schedulers/flags.py`
2. `backend/scripts/run_scheduler_worker.py` → `~/backend/scripts/run_scheduler_worker.py`
3. `backend/scripts/__init__.py` → `~/backend/scripts/__init__.py`

PERHATIAN ACK (3 Sep 2026): `deploy_kantorteman.sh` sekarang ber-ACK-gate — tanpa
`KT_DEPLOY_ACK=deploy` script hanya DRY-RUN (0 SSH). Argumen tak dikenal DITOLAK (exit 2),
tidak ada fallback deploy. Jalur kanonis per file:

    KT_DEPLOY_ACK=deploy bash /root/.hermes/shared/scripts/deploy_kantorteman.sh \
        --file <path-file-repo> --no-restart

`--no-restart` WAJIB di jalur ini — tanpa itu script men-touch `tmp/restart.txt`
(Passenger reload) padahal web app tidak berubah (pitfall lama, runbook ini TANPA restart).
Ketiga upload ini bisa dibungkus satu perintah ACK-gated:
`KT_SCHED_GOLIVE_ACK=deploy bash scripts/scheduler_golive.sh upload`
(3 file kanonis berurutan, BERHENTI di kegagalan pertama, lalu verifikasi ukuran byte
remote == lokal per file — jangan lanjut `activate` bila verify gagal).

Hardening jalur upload (3 Sep 2026, tick E2E raka — DRY-RUN + sandbox test, 0 SSH ke prod):
- `--file` kini DIVALIDASI: path relatif di-resolve absolut, file di luar
  `backend/` repo DITOLAK (exit 2). Tanpa ini, `--file backend/scripts/x.py`
  lolos `-f` check lalu terpetakan ke `~/backend/backend/*` (folder nested yang
  ADA di server) → upload "sukses" tapi live root tidak berubah (nested-trap).
- `deploy_file()` kini `mkdir -p` dir remote dulu + verifikasi ukuran byte
  remote == lokal (output `OK (NB)` / `FAIL [...]`) — bukti file utuh di server,
  bukan cuma "base64 -d sukses".
- DRY-RUN kini menampilkan mapping `Lokal:` → `Remote:` → jalur upload 3 file
  bisa diverifikasi 100% sebelum ACK. Bukti test matrix: `outputs/rpm-raka-e2e-latest.md`
  tick 3 Sep ~16:1x WIB (T1–T8 PASS, termasuk size-tamper FAIL).
- Harness 0-SSH khusus `scheduler_golive.sh`: `backend/scripts/test_scheduler_golive_sh.sh`
  (12/12 PASS, stabil multi-run; mock GOLIVE_SSH_CMD/curl/PATH — zero SSH & jaringan).
  Cakupan: gate ACK default-deny (tanpa `KT_SCHED_GOLIVE_ACK=deploy` → exit 3, 0 panggilan
  ssh), status/verify read-only, nested-layout guard, activate baris crontab kanonis
  (--once + flock, verifikasi panjang string), rollback hanya hapus crontab, upload
  3 file kanonis stop-on-first-fail + verify ukuran. Main `3b08937` (4 Sep 2026,
  branch `feat/raka-golive-gate-test` dd9c16e).

Kenapa TANPA `main.py` dan TANPA restart:
- `main.py` LIVE tidak import `app.schedulers.flags` (hanya `outreach_machine` + apscheduler
  lama) → upload flags.py/worker TIDAK mengubah proses web sama sekali.
- Worker `--once` import `main` LIVE (bukan repo). Live `main.py` SUDAH punya semua runner
  yang dipanggil `_job_runners` (`_run_async_job`, `scheduled_followup_processor`,
  `_run_outreach_lifecycle`, `_run_subscription_deductions`, `_run_project_billing_invoices`)
  — diverifikasi grep di server 1 Sep 23:1x WIB. Preflight cek ini otomatis
  (`runner --once kompatibel dgn main.py live`).
- Web app tidak berubah → tidak perlu `tmp/restart.txt` → risiko API = nol.

Setelah 3 file masuk: `bash scripts/scheduler_golive.sh status` (flags.py/worker harus ADA,
master tetap `false`, health 200) → `activate` (crontab `--once` + 1x run manual via flock)
→ `verify` (log `once selesai`).

Langkah saat Kevin bilang "deploy" (SSH `deploy-kantorteman`, dir `~/backend`):

1. Preflight penuh harus READY dulu: `backend/venv/bin/python scripts/preflight_scheduler_deploy.py --remote --tests` (exit 0, 0 FAIL).
2. Upload 3 file jalur upload (§ Jalur Upload First-Enable di atas): `app/schedulers/flags.py`,
   `scripts/run_scheduler_worker.py`, `scripts/__init__.py` — TANPA `main.py` (live main.py
   beda dari repo & TIDAK perlu diubah; worker `--once` kompatibel dgn main live, preflight
   yang cek). Verify tiap file: `grep -c` marker di server.
   Bungkus 1 perintah ACK-gated (urutan, stop-on-first-fail & verifikasi ukuran
   remote==lokal sama persis, test 16/16 lokal 0-SSH, main=f42651f):
   `KT_SCHED_GOLIVE_ACK=deploy bash scripts/scheduler_golive.sh upload`
3. `bash scripts/scheduler_golive.sh status` → flags.py/worker ADA, master tetap `false`,
   health 200. `--probe` via SSH: `master: false`, `will_start: false`, exit 0.
4. `KT_SCHED_GOLIVE_ACK=deploy bash scripts/scheduler_golive.sh activate` → pasang crontab
   `--once` (idempotent) + 1x run manual via flock. Crontab kanonis (followup saja, process-local,
   tidak tulis `.env`):
   `20 * * * * flock -n /tmp/kt-sched.lock /home/qqwtlphb/virtualenv/backend/3.13/bin/python /home/qqwtlphb/backend/scripts/run_scheduler_worker.py --safe-first --once >> /home/qqwtlphb/backend/scheduler-worker.log 2>&1`
5. Bukti jalan: log `[SCHEDULER] once: run followups ...` + `once selesai` (`verify`).
6. E2E prod: 1 lead uji masuk sequence → status berubah + audit NO_CLICK_FOLLOWUP.
   (145 lead "Scraped" TIDAK otomatis terselamatkan — 0 sequence aktif. Outreach = keputusan bisnis.)
7. Rollback: `KT_SCHED_GOLIVE_ACK=deploy bash scripts/scheduler_golive.sh rollback` (hapus 1
   baris crontab). `.env` web + Passenger tidak disentuh — proses web tidak pernah direstart.

Lifecycle (hourly) = ACC terpisah (`--enable followup,lifecycle`). Billing/blast = ACC terpisah lagi.


## Web Preview per-Lead (blast WA → simulasi web hot prospect) — feat/raka-blast-web-preview

Fitur: saat blast, lead status "Prospek Panas" otomatis dapat landing simulasi web per-industri
(swap nama bisnis/nomor WA ke data lead). Link `{frontend}/wp/{slug}` disisipkan di pesan WA
(placeholder `{{web_preview_link}}` atau ditambah otomatis di akhir). Pembukaan link ditrack
(web_previews.opened_count + LeadActivityLog WEB_PREVIEW_OPENED).

File baru:
- backend/models/web_preview.py (tabel web_previews — migrate.py sudah ditambah, jalankan `python migrate.py`)
- backend/app/services/web_preview_service.py (registry template + swap engine)
- backend/routers/web_preview.py (POST /api/web-preview/generate/{lead_id} admin,
  GET /api/web-preview/lead/{lead_id} auth, GET /wp/{slug} publik + tracking)
- backend/web_preview_templates/{klinik,bengkel,kontraktor}.html + backend/web_preview_assets/{key}/ (6.2MB)
- frontend next.config.js: rewrite /wp/:slug → backend

Langkah deploy (setelah GO Kevin):
1. Upload file .py via deploy_kantorteman.sh --file (models/web_preview.py, app/services/web_preview_service.py,
   routers/web_preview.py, app/services/campaign_service.py, main.py — CEK drift main.py live dulu).
2. Upload aset: rsync backend/web_preview_assets/ → ~/backend/uploads/web_preview_assets/ (sekali, 6.2MB).
3. `python migrate.py` di server (buat tabel web_previews) — aman, hanya CREATE bila belum ada.
4. Merge frontend ke main → Vercel deploy otomatis (rewrite /wp).
5. Uji: generate preview 1 lead via POST API → buka /wp/{slug} → cek gambar + track opened_count.

Catatan: template bank v1 = 3 industri (klinik/bengkel/kontraktor; kontraktor default). Template lain
(tokobangunan, EO, dll) tinggal tambah file + entry REGISTRY + aset. Gagal generate preview TIDAK
memblokir blast (try/except, log [WEB_PREVIEW]).

Netralisasi klaim fiktif (6 Sep 2026, ACC Kevin "eksekusi aja semuanya", commit facd7b4/cb6af0d):
REGISTRY['sanitize'] tiap template juga menimpa klaim fiktif yang keliatan asli sebelum render
per-lead — nama orang/perusahaan (Ibu Ratna, PT Bina Logistik, Ir. Hartono, 5 dr. klinik),
garansi spesifik (Garansi 5 Tahun → Garansi Tertulis; garansi 7 hari bengkel → netral),
angka personel (42), berita fiktif (Ruko Damai Bahagia, jadwal sewa Nov 2026, Sepinggan),
nama proyek/lokasi template bank (Balikpapan/Sepinggan/Karang Joang) → generik. Sengaja DIBIARIN:
angka filler desain (128 proyek, 98%, 16 tahun, jadwal klinik, tahun portfolio) + struktur desain.
Test: test_render_neutralizes_fictive_claims. Preview lama (sebelum patch) TIDAK otomatis ke-render
ulang — reuse slug lama; regenerate force_new bila butuh versi bersih.

Template bank diperluas (8 Sep 2026, commit 23eadd6 → 5d044e4 — DEPLOYED ke prod 8 Sep,
GO Kevin "selesain sampai akhir baru deploy"): REGISTRY 3 → 19 vertikal aktif. +15 template ACC
dari _refshots (otomotif, salon, konsultan, konveksi, interior, percetakan, tokobangunan, laundry,
properti, bimbel, konstruksi-kecil, eo-wedding, jasa-b2b, hukum, travel). Beda pola dgn bundle 6 Sep: klaim fiktif di-neutralize IN-FILE
(baked di bank copy — garansi berangka otomotif/konstruksi-kecil/jasa-b2b, tahun berdiri salon/travel;
WA CTA otomotif di-wire 15 link wa.me, sebelumnya href="#" mati) karena ada perubahan struktural yang
tidak bisa render-pair; file sumber bersih tetap di _refshots/auto-web-prospek. Kafe masuk juga di
deploy yang sama (5d044e4): 14 foto menu kafe_m_*.jpg digenerate ulang via imaginer (lama hilang dari
disk; sample vision 3/3 bersih, tanpa teks), REGISTRY +kafe. QA staging PASS (aset termuat via symlink;
QA bank copy mentah = broken-img false positive karena path aset cuma resolve via rewrite /uploads).
eo-wedding dup basename 01.jpg
(v4 vs v4b) dipisah → tablescape.jpg. Kontraktor gen1-7.jpg dilengkapi di repo copy (sumber: _refshots).
Deploy step tambahan dgn langkah 1-5 di atas: rsync backend/web_preview_assets/ ke server (asets baru
15 key, termasuk kontraktor gen1-7) SEBELUM restart — kalau tidak, render template baru broken-img.
WAJIB (lesson 8 Sep): upload JUGA backend/web_preview_templates/*.html → ~/backend/web_preview_templates/
(tar+base64 via ssh, tar -C /home/qqwtlphb/backend) — PRODUCTION.md runbook lama cuma nyebut aset;
tanpa ini _render FileNotFoundError fail-open → preview lead baru blank. Verifikasi deploy:
md5 service == remote, `grep -c` marker, REGISTRY=19 via venv python, render test in-memory
(select_template_key + _render dgn Lead dummy: swap brand/aset OK, WA fallback kalau lead tanpa
nomor = by-design), curl /wp/<slug-lama> 200. Buktinya: openapi 200, ROW slug kontraktor lead 163 OK.
select_template_key = skor keyword (bukan urutan): keyword baru HANYA nambah match di niche kosong,
dua template kena skor sama → entry lama (klinik/bengkel/kontraktor) menang tie-break.

Template bank +2 vertikal (9 Sep 2026, commit `ad01bbe` — DEPLOYED ke prod 9 Sep, ACC Kevin
"acc atk" di topic 304 merespons caption verdict 16795 yang menawarkan ACC → bundel 21 + deploy):
REGISTRY 19 → 21 (+`atk` = toko ATK/print/langganan kantor "Toko Aneka Karya", +`alatberat` =
sewa alat berat/excavator "Tunas Alat Berat"). Source: _refshots/atk-v2.html (file yang "hilang"
2 Sep ternyata nyasar nama v1 dengan isi v2 lengkap; dikembalikan ke nama atk-v2 8 Sep) dan
alatberat-v2.html (ACC 8 Sep). Sanitize in-file: garansi spesifik "garansi tukar 7 hari" →
"garansi tukar" (aturan garansi spesifik → netral). QA staging 2/2 PASS (aset termuat via symlink).
Deploy: aset 8 jpg dulu (md5 8/8 identik) → template 2 html (md5 match) → service via deploy script
(md5 match, grep '"title":' = 21) → restart-only → verif: import OK, REGISTRY=21, render test
in-memory atk+alatberat (select/WA rewrite/asset rewrite OK, sanitize OK) + default kontraktor,
openapi 200, /wp/<slug lead 163> 200 26KB. Pitfall ulang terdokumentasi: multiline python -c via
ssh = quote-mangling (SyntaxError diam-diam) → script via base64 → /tmp/ + PYTHONPATH.


## PageSpeed Scoring Lead (kolom + auto-check + endpoint + cron) — feat/raka-pagespeed-leads

Fitur: setiap lead dengan `website_url` dapat skor PageSpeed Insights (mobile, 0-100) + timestamp
`last_speed_check`. Sinyal web pain buat prioritas WA. Skor NULL = belum pernah dicek.

File:
- models/lead.py: +kolom `page_speed_score` INT NULL, `last_speed_check` VARCHAR (pola last_followup_at)
- migrate.py: 2 tuple di `_migrations` (MySQL) + 2 block SQLite — idempotent, `python migrate.py` di server
- app/services/pagespeed_service.py BARU: PSI v5 call (env `PAGESPEED_API_KEY` dulu, fallback
  `google_api_key` dari settings DB), `is_gating_web()` (IG/Linktree/wa.me/shortlink), fail-open total
- routers/leads.py: auto-check background saat scrape (`/api/search`) dan manual create; endpoint
  `POST /api/leads/{id}/speed-check` (sync, admin); `GET /api/leads?hot_list=true[&hot_max_score=60]`
  (no web / skor rendah / web gating); LeadOut +2 field
- scripts/run_pagespeed_recheck.py BARU: re-check mingguan lead aktif (status bukan closed/deal/klien),
  web belum dicek atau stale >7 hari; `--dry-run`, `--limit`, sleep 1.5s antar call, fail-open

Cron mingguan (crontab hosting, BUKAN APScheduler web) — Senin 09:07 WIB (kanonis):
  `7 9 * * 1 flock -n /tmp/kt-pagespeed.lock /home/qqwtlphb/virtualenv/backend/3.13/bin/python /home/qqwtlphb/backend/scripts/run_pagespeed_recheck.py >> /home/qqwtlphb/backend/logs/pagespeed_recheck.log 2>&1`
  Script sudah chdir sendiri — JANGAN sisipkan `cd` dalam `flock` (builtin, exec gagal
  exit 69 → no-op diam-diam). Verifikasi tiap pasang: lock mtime + log berisi + skor terisi.

⚠️ STATUS 7 Sep 2026 (audit malam raka): crontab live MASIH versi lama yang rusak
  (`flock ... cd ... && python`) → Senin 07 Sep 09:07 WIB first-run = NO-OP total
  (bukti: `/tmp/kt-pagespeed.lock` mtime 07 Sep 09:07, log absen, 0/148 lead terisi
  skor). Ganti 1 baris crontab jadi kanonis di atas — itu mutasi prod, butuh go
  Kevin/day-shift; JANGAN anggap "terpasang = jalan" tanpa first-run terverifikasi.
  Backfill manual (`--dry-run` lalu eksekusi) juga belum pernah dilakukan.

FIXER (raka, 9 Sep 2026 — test lokal 13/13 PASS + status live prod 09:19 WIB):
  `backend/scripts/fix_pagespeed_crontab.sh` — status (read-only, verdict
  CANONICAL/BUGGY/ABSENT) | fix [GATE: KT_PAGESPEED_FIX_ACK=deploy, backup crontab
  otomatis ke $HOME/crontab-backup-pagespeed-<ts>.txt, idempotent, verifikasi
  pasca-fix] | verify. Tanpa ACK → exit 3 zero mutasi (terbukti live). Jalankan:
    bash backend/scripts/fix_pagespeed_crontab.sh status          # read-only
    KT_PAGESPEED_FIX_ACK=deploy bash backend/scripts/fix_pagespeed_crontab.sh fix
    bash backend/scripts/fix_pagespeed_crontab.sh verify
  First-run Senin berikutnya 09:07 WIB = bukti sesungguhnya (lock mtime baru +
  log berisi + skor terisi).

Langkah deploy:
1. Upload: models/lead.py, migrate.py, app/services/pagespeed_service.py, routers/leads.py,
   app/services/lead_service.py, schemas/lead.py, scripts/run_pagespeed_recheck.py
2. Import test `python -c 'import main'` di server → migrate.py → restart Passenger → cek openapi.
3. Backfill skor pertama: `python scripts/run_pagespeed_recheck.py --dry-run` lalu eksekusi.

KETERGANTUNGAN (6 Sep 2026): PageSpeed Insights API belum ENABLE di project Google yang memegang
key prod (Places) → call PSI = HTTP 403. Tanpa key = 429 quota per-IP. Fix: enable "PageSpeed
Insights API" di Google Cloud Console (gratis) — setelah itu fitur langsung hidup (key fallback
dari settings DB, tanpa env baru). Sebelum enable: semua call fail-open, skor tetap NULL, tidak
mengganggu scrape/blast/cron.

UPDATE 11 Sep 2026 (raka, tick pagi): **PSI API SUDAH ENABLE** — probe dari server PSI_HTTP=200
(sebelumnya 403 sejak 6 Sep; dep sisi Kevin selesai). Backfill jalan 2x:
- 08:34–08:47 WIB (manual, sumber tak tercatat — day-shift?): ~31 lead scored (skor 55–100).
- 09:13 WIB (raka): FATAL mid-batch — 12 lead dead-site beruntun (PSI 400 ≈10s/lead, tanpa
  commit = koneksi idle) kena **MySQL wait_timeout=120s** → "server has gone away"; skor
  lead 285 hilang, 6 lead sisa tak diproses. Sweep ulang 09:2x dengan session-per-lead:
  lead 285 skor 44 + lead 323 skor 68 + 5 fail-open (dead-site/NO_FCP/timeout), **0 FATAL**.
  Total scored prod: **34 lead** (dari 0 sebelum 11 Sep).
- FIX `feat/raka-pagespeed-session-per-lead` (9bbe3cb, test 16/16 PASS): fase eksekusi
  run_pagespeed_recheck.py pakai session baru per lead + try/except per lead = kebal
  idle-kill. **BELUM di-deploy** (upload file prod tunggu ACC Kevin). Tanpa fix, cron
  Senin 09:07 berisiko FATAL lagi kalau dead-site kandidat teratas (fail streak >120s
  tanpa commit) — sisa lead menunggu minggu berikutnya (fail-open, tidak merusak data).

UPDATE 11 Sep 2026 ~23:1x WIB (qnight raka, verifikasi live — supersede "BELUM di-deploy" di atas):
- Script versi session-per-lead + dead-site-policy **SUDAH DI-UPLOAD ke prod 22:01:43 WIB** oleh
  Kevin — sha256 `6b118fae…` = identik repo `1ccdfa8`. Blocker "tunggu ACC upload" SELESAI.
- Backfill 22:0x–22:25 WIB (log `logs/pagespeed_recheck_backfill_20260911.log`): summary
  `{checked: 1, failed: 15, skipped: 0, recorded_dead: 13}` — lead 210 skor 72; 13 dead-site
  tercatat skor 0; lead 315 + 320 PSI timeout → tetap NULL, retry Senin. ERP verified 23:0x:
  **48 lead scored** (35 skor>0 + 13 skor=0), `last_check` max 22:08 WIB.
- Kebijakan dead-site (Kevin 11 Sep, `1ccdfa8`): PSI 400 FAILED_DOCUMENT_REQUEST/NO_FCP = situs
  gagal diukur → `page_speed_score=0` + `last_speed_check` WIB, commit per lead. Timeout /
  key-error / quota → tetap NULL + retry cron berikutnya (jangan salah label mati). Kalau situs
  hidup lagi, skor asli menggantikan 0 (auto-retry via stale-days).
- Cron Senin 14 Sep 09:07 jalan **versi BARU ini** (crontab kanonis, dibaca langsung 23:05 WIB).
  First-run verification tetap wajib: lock mtime baru + `logs/pagespeed_recheck.log` terbentuk +
  skor naik dari 48.
- GOTCHA transfer file ke hosting KT: **scp manual = SILENT-FAIL** (file tak tertulis, mtime
  diam-diam). Jalur sah = base64-over-ssh (`deploy_kantorteman.sh` sudah begitu + verifikasi
  byte/sha pasca-upload — byte-verify inilah yang menutup silent-fail ini).
- Gotcha ops: watcher `while pgrep -f run_pagespeed_recheck; do sleep 30; done` (PID 902892,
  live 23:0x) tak pernah selesai — `pgrep -f` match cmdline watcher-nya sendiri, jadi marker
  "BACKFILL-DONE" tak ke-print walau backfill kelar. Aman (sleep loop); kill PID kalau mau
  bersih. Pelajaran: cek proses via `pgrep -f` → hindari pattern yang nempel di cmdline watcher.
