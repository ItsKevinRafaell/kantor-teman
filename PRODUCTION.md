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

Status terverifikasi 31 Agu 2026 22:2x WIB: API prod 200 (root-cause 500 = `schemas/board.py`
stale tanpa `BoardCardChecklistUpdate`, hotfix masuk 22:11:50 + restart 22:12:56). Worker +
flags.py BELUM di server. E2E lokal PASS: `backend/venv/bin/python scripts/e2e_lifecycle_local.py`
(lead WA_Terkirim + proposal 72h → "Follow Up" + audit NO_CLICK_FOLLOWUP, sqlite throwaway).

Langkah saat Kevin bilang "deploy" (SSH `deploy-kantorteman`, dir `~/backend`):

1. Sinkron kode worker (checksum, jangan rsync --delete):
   `rsync -rc --out-format='%n' backend/app/schedulers/flags.py backend/scripts/run_scheduler_worker.py deploy-kantorteman:backend/tmp-sync/` lalu pindah ke path final; atau `git -C ~/backend pull` jika branch sudah di-merge ke main.
2. `.env` prod: TAMBAH `ENABLE_FOLLOWUP_SCHEDULER=true` + `ENABLE_LIFECYCLE_SCHEDULER=true`
   (billing: `ENABLE_BILLING_SCHEDULER=true` hanya kalau Kevin mau; blast TETAP tidak diset).
   `ENABLE_BACKGROUND_SCHEDULER` biarkan `false` — worker web Passenger tidak boleh jalankan scheduler.
3. Backup dulu: `cp backend/.env backend/.env.bak-enable-scheduler-$(date +%Y%m%d-%H%M%S)`.
4. Start worker terpisah:
   `cd ~/backend && nohup /home/qqwtlphb/virtualenv/backend/3.13/bin/python scripts/run_scheduler_worker.py >> scheduler-worker.log 2>&1 &`
   Blast-gate aktif: kalau `ENABLE_BLAST_SCHEDULER` true tanpa `--allow-blast`, worker REFUSE (exit 3).
5. Verifikasi: `tail -5 scheduler-worker.log` harus ada `[SCHEDULER] worker started, jobs aktif: followup,lifecycle`
   (atau + `billing`), dan `--probe` sebelum start mencetak rencana flag.
6. E2E prod setelah jalan: lead uji baru masuk sequence → cek `leads.status` berubah + baris audit
   rule NO_CLICK_FOLLOWUP → laporan/card terbentuk di board.
7. Rollback: `kill` proses worker, restore `.env` dari backup, `touch tmp/restart.txt`.

Lock repo lokal: `.fleet-lock` saat ini dipegang sesi mati `raka/wa-multi-number-deploy`
(pid 682418 sudah tidak ada, lock < 2 jam — script menolak takeover otomatis). Kerja branch ini
(`feat/raka-e2e-scheduler-enable`) tidak commit ke `main` sehingga aman; merge ke `main` oleh
raka owner setelah ACC deploy.
