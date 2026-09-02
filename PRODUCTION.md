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
3. Aktif via crontab mode `--once` (job jalan 1x lalu exit — tidak ada daemon yang bisa dibunuh cron/timeout sebelum fire pertama, karena APScheduler fire pertama = now+interval):
   `20 * * * * flock -n /tmp/kt-sched.lock python3 /home/qqwtlphb/backend/scripts/run_scheduler_worker.py --safe-first --once >> /home/qqwtlphb/backend/scheduler-worker.log 2>&1`
   → cadence hourly (JOB_TRIGGERS: `followups` interval 1 jam); offset menit bebas, `flock -n` mencegah overlap.
4. Bukti jalan (SELESAI kalau semua ada): log `scheduler-worker.log` berisi `[SCHEDULER] once: run followups ...` + `once selesai`, dan e2e: 1 lead masuk sequence → followup terjadwal terproses.
5. Level berikutnya (masing-masing butuh ACC eksplisit Kevin, jangan sekalian di-crontab): blast hanya via daemon `--allow-blast` (interval 1 menit), JANGAN lewat `--once`; billing crontab harian sesuai JOB_TRIGGERS (`subscription-deductions` 00:05, `project-billing-invoices` 00:15) hanya setelah Kevin override PLAN-report-invoice.

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

File yang perlu masuk server (base64 via `deploy_kantorteman.sh --file`, verifikasi tiap file
dengan `grep -c` marker di server — "Deploy complete" TIDAK membuktikan apa-apa, lihat pitfall 0):

1. `backend/app/schedulers/flags.py` → `~/backend/app/schedulers/flags.py`
2. `backend/scripts/run_scheduler_worker.py` → `~/backend/scripts/run_scheduler_worker.py`
3. `backend/scripts/__init__.py` → `~/backend/scripts/__init__.py`

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
