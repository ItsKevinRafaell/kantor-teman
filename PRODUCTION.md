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
ENABLE_BACKGROUND_SCHEDULER="true"
FONNTE_WEBHOOK_SECRET=""
```

Catatan:

- Jangan mengganti `SECRET_ENCRYPTION_KEY` jika sudah ada data brankas terenkripsi.
- Isi `FONNTE_WEBHOOK_SECRET` hanya jika provider webhook dapat mengirim header `x-fonnte-webhook-secret`. Jika diisi, callback tanpa header tersebut ditolak.
- Scheduler memproses antrean blast setiap menit, follow-up setiap jam, dan auto-deduct langganan setiap hari.
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
