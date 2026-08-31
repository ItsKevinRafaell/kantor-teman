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
- Di shared hosting Passenger/cPanel, biarkan `ENABLE_BACKGROUND_SCHEDULER="false"` supaya setiap worker web tidak menjalankan scheduler sendiri. Jalankan scheduler hanya dari worker/process terpisah: `python3 scripts/run_scheduler_worker.py --probe` dulu (cetak rencana flag, tidak start job). Start blocking: `python3 scripts/run_scheduler_worker.py` — sub-flag ON saja. Blast ditolak kecuali `--allow-blast` (ACC Kevin). Sub-flag: `ENABLE_BILLING_SCHEDULER`, `ENABLE_FOLLOWUP_SCHEDULER`, `ENABLE_LIFECYCLE_SCHEDULER`, `ENABLE_BLAST_SCHEDULER` (default semua false).
- Snapshot env prod 30 Agu 2026 (SSH read-only `qqwtlphb`): `.env` hanya `ENABLE_BACKGROUND_SCHEDULER=false`, sub-flag absen, `flags.py` + worker **belum** di server, `stderr.log` 0 APScheduler. Tes pengunci: `tests/test_scheduler_prod_snapshot.py`. Jangan nyalain master di `.env` Passenger.
- API key provider dapat diatur dari menu admin setelah deploy.

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
