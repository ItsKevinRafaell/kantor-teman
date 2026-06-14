# LeadBot Admin Guide

Updated: 2026-06-14

LeadBot adalah asisten sales WhatsApp untuk UMKM. Fokus operator: lihat inbox, isi data usaha, cek status Fonnte, tes jawaban AI, dan ambil alih chat kalau pelanggan butuh admin.

## Akses Dashboard

Production:

```text
https://autolead.kantorteman.my.id/
```

Local/VPS:

```text
http://127.0.0.1:3000/
```

Jika dashboard auth aktif, login memakai email akun dashboard yang tersimpan di database. Environment `DASHBOARD_EMAIL`/`DASHBOARD_PASSWORD` hanya dipakai untuk bootstrap user pertama saat tabel masih kosong. Jangan tulis credential di dokumen atau chat.

Reset password:

- Buka `/reset-password`.
- Gunakan email resmi sesuai `AUTH_ALLOWED_EMAIL_DOMAINS`, default `temanumkmkita.com`.
- SMTP sender production memakai `noreply@temanumkmkita.com`.
- Password SMTP hanya boleh ada di environment production, bukan di repo atau chat.

## Alur Harian Operator

1. Buka dashboard dan cek status ringkas di header.
2. Pastikan Fonnte aktif di environment production.
3. Isi atau perbarui Data Usaha.
4. Upload dokumen penting seperti pricelist, FAQ, katalog, SOP, atau promo aktif.
5. Pakai AI Test untuk cek apakah jawaban sudah aman dan jelas.
6. Pantau percakapan masuk.
7. Balas manual untuk chat sensitif, harga khusus, komplain, refund, atau permintaan yang belum ada datanya.

## Inbox / Percakapan

Fungsi utama:

- Melihat chat pelanggan.
- Melihat stage dan score lead dari AI.
- Membalas manual lewat WhatsApp/Fonnte.
- Pause atau resume auto-reply AI per percakapan.
- Eskalasi chat yang perlu admin.
- Menutup percakapan yang selesai.

Perilaku penting:

- Saat admin membalas manual, auto-reply AI untuk percakapan itu dipause.
- Jika ingin AI lanjut membalas, aktifkan lagi auto-reply pada percakapan tersebut.
- AI harus bertanya balik jika data kurang; AI tidak boleh mengarang harga, stok, diskon, refund, garansi, alamat, atau janji layanan.

## Data Usaha

Gunakan Data Usaha untuk memberi konteks aman ke AI:

- Profil usaha
- Produk atau layanan
- Harga dan paket
- Cara order
- Jam operasional
- Area layanan
- Promo aktif
- FAQ
- Batasan layanan
- Kontak admin

Tulis dengan bahasa yang biasa dipakai owner UMKM. Hindari instruksi teknis panjang kalau operator non-teknis yang akan memelihara datanya.

## Upload Dokumen

Upload dokumen dipakai untuk menambah knowledge AI.

Contoh dokumen yang cocok:

- Pricelist PDF
- Katalog produk
- FAQ
- SOP follow-up
- Syarat garansi/refund
- Detail paket layanan

Setelah upload, uji dengan AI Test sebelum membiarkan AI membalas pelanggan real.

## AI Test

AI Test dipakai untuk simulasi pertanyaan pelanggan.

Contoh prompt:

```text
Saya mau buat website untuk usaha catering. Harganya berapa?
```

Cek hasilnya:

- Jawaban singkat dan ramah.
- Tidak mengarang harga jika data harga belum ada.
- Bertanya satu hal lanjutan yang relevan.
- Menandai `needsAdmin` untuk kasus sensitif.

## WhatsApp / Fonnte

LeadBot tidak mengelola pairing device, QR, atau session WhatsApp sendiri. Semua pairing device dilakukan di dashboard Fonnte. LeadBot hanya:

- menerima webhook inbound di `POST /api/webhook`;
- mengirim outbound lewat Fonnte API;
- menampilkan apakah token Fonnte sudah terkonfigurasi.

Real-send hanya boleh dites ke nomor internal yang disetujui. Jangan gunakan nomor klien untuk smoke test.

## KantorTeman Bridge

KantorTeman bisa mengirim outbound ke AutoLead lewat:

```text
POST /api/integrations/kantorteman/whatsapp/send
```

Mode aman default:

```text
KANTORTEMAN_BRIDGE_DEMO=true
```

Dalam demo mode, pesan dari KantorTeman hanya dicatat ke inbox LeadBot, tidak dikirim ke WhatsApp real. Matikan demo mode hanya setelah token Fonnte valid dan sudah dites ke nomor internal.

## Telegram Admin

Telegram admin dapat dipakai untuk notifikasi dan balasan manual jika bot/token sudah dikonfigurasi.

Prinsip operator:

- Pakai command yang sudah disediakan.
- Untuk manual reply, pastikan nomor/chat target benar.
- Manual reply akan mem-pause auto-reply AI pada percakapan terkait.

## API Ringkas

Health:

```text
GET /api/health
```

Dashboard:

```text
GET  /api/dashboard/stats
GET  /api/dashboard/conversations
GET  /api/dashboard/conversations/:id
POST /api/dashboard/conversations/:id/reply
POST /api/dashboard/conversations/:id/auto-reply
POST /api/dashboard/conversations/:id/escalate
POST /api/dashboard/conversations/:id/close
GET  /api/dashboard/leads
GET  /api/dashboard/whatsapp/status
```

Knowledge:

```text
GET    /api/dashboard/knowledge
PUT    /api/dashboard/knowledge
POST   /api/dashboard/knowledge/wizard
GET    /api/dashboard/knowledge-items
POST   /api/dashboard/knowledge-items
PUT    /api/dashboard/knowledge-items/setup
PUT    /api/dashboard/knowledge-items/:id
DELETE /api/dashboard/knowledge-items/:id
GET    /api/dashboard/knowledge/uploads
POST   /api/dashboard/knowledge/upload
```

AI:

```text
POST /api/dashboard/ai/test
```

Webhook/bridge:

```text
POST /api/webhook
GET  /api/integrations/kantorteman/health
POST /api/integrations/kantorteman/whatsapp/send
```

## Command Operasional

Jalankan di VPS sesuai process manager yang aktif:

```bash
pm2 status
pm2 logs leadbot --lines 80
pm2 restart leadbot --update-env
```

Health check:

```bash
curl -fsS https://autolead.kantorteman.my.id/api/health
```

Jangan print token, password, `.env`, atau API key ke chat.
