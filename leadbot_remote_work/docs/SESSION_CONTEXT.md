# Session Context

Dokumen ini menyimpan konteks kerja terbaru agar session berikutnya tidak mulai dari nol.

## Scope Penting

- Fokus project hanya VPS `/opt/leadbot`.
- Jangan sentuh project lokal `/home/kevin/kantorteman`.
- Jangan sentuh project KantorTeman sampai flow LeadBot lokal stabil.
- Bahasa UI dan copy harus Indonesia.
- User ingin tool yang UMKM-friendly, bukan dashboard teknis.

## Keputusan Produk Terbaru

Masalah utama bukan kurang template, tapi arsitektur bot masih statis. Jika user harus membuat 100 pola jawaban, produk akan sulit dipakai UMKM.

Keputusan arah:

- `Pola Jawaban` tidak boleh menjadi otak utama.
- `Pola Jawaban` harus turun menjadi `Aturan Khusus` atau override.
- Otak utama baru adalah `Answer Engine`:
  - deteksi intent
  - ekstrak detail
  - ambil fakta dari data usaha
  - susun jawaban multi-intent
  - AI hanya optional untuk polish/fallback
  - manusia hanya untuk data tidak cukup atau risiko salah

Plan detail ada di:

`docs/ANSWER_ENGINE_PLAN.md`

Next session harus mulai dari dokumen itu, terutama `Milestone 1 - Backend Foundation`.

## Kondisi App Terakhir

- App live: `http://202.6.204.179:20035/`
- PM2 app: `leadbot`
- Health terakhir setelah perubahan: `200`
- Mode terakhir dari health: `ai_first`
- Dashboard login masih aktif.
- Data `knowledge` terakhir masih default/kosong, belum ada produk/harga/FAQ real.
- Repo bersih setelah commit plan.

## Yang Sudah Dikerjakan Sebelum Dokumen Ini

### UI Dashboard

Beberapa perubahan UI yang sudah live:

- Login page sudah dibuat lebih proper dan branded.
- Top bar sudah diganti menjadi sidebar.
- Bahasa UI diarahkan ke Indonesia.
- Font diseragamkan ke Poppins.
- Palette disesuaikan:
  - Optimism Yellow `#f5a700`
  - Dark Charcoal `#242423`
  - Pure Snow `#fcfaf7`
- Dark mode sudah ada.
- Logout sudah ada.
- Menu utama saat terakhir:
  - `Hari Ini`
  - `Percakapan`
  - `Prospek`
  - `Info Usaha`
  - `Panduan`
- Halaman `Panduan` sudah ada untuk workflow penggunaan.
- Halaman `Info Usaha` dibuat lebih UMKM-friendly:
  - Data usaha
  - Kesiapan bot
  - Coba jawaban bot
  - Pengaturan lanjutan

### Pola Jawaban

Commit penting:

`27897f2 feat(bot): improve reply pattern management`

Perubahan:

- `Pola Jawaban Lanjutan` dibuat lebih mudah dibaca.
- Pola aktif dikelompokkan per kategori.
- Trigger tampil sebagai chip kecil.
- Jawaban bot dipisahkan dalam blok baca.
- Pola nonaktif disembunyikan di bagian collapse.
- Form tambah/edit diubah copy-nya:
  - `Kata atau kalimat pelanggan`
  - `Jawaban siap pakai`
  - `Bobot pilihan`
- UI menjelaskan bahwa jika satu chat cocok dengan beberapa pola, sistem memilih niat paling spesifik.

### Matching Multi Trigger

Sebelumnya engine keyword terlalu didominasi `priority * 10`, sehingga sapaan seperti `halo` bisa menang atas harga/order.

Sekarang scoring keyword sudah dituning:

- Exact/frasa dihitung.
- Jumlah trigger yang cocok dihitung.
- Kategori intent punya bobot.
- Priority tetap ada tapi tidak mendominasi.
- Sapaan dan penutup diberi bobot rendah.
- Frasa tidak boleh match hanya karena satu kata kecil cocok.

Test terakhir:

- `halo kak harga dan cara order gimana?` -> `Pesanan`
- `stok ready? harganya berapa dan alamat di mana?` -> `Harga`
- `saya tertarik, ada promo dan bisa kirim?` -> `Promo`
- `saya mau meeting dan butuh invoice pembayaran` -> `Pembayaran`
- `halo kak` -> `Pembuka`
- `terima kasih kak` -> `Penutup`

### Template Siap Pakai

Commit penting:

`5806285 feat(bot): add ready reply templates`

Ada 18 template aktif:

- Pembuka
- Produk
- Harga
- Promo
- Pesanan
- Konsultasi
- Lokasi
- Pengiriman
- Pembayaran
- Ketersediaan
- Jam Operasional
- Ketentuan
- Request Khusus
- Follow Up
- Closing
- Klarifikasi
- Penutup
- Di Luar Konteks

Ada 7 legacy/test keyword yang dinonaktifkan.

## Arsitektur Saat Ini

File penting:

- `src/routes/webhook.js`
- `src/services/aiService.js`
- `src/services/keywordService.js`
- `src/services/knowledgeService.js`
- `src/services/escalationService.js`
- `src/services/modeService.js`
- `src/routes/dashboard.js`
- `public/index.html`
- `src/migrate.js`

Flow sekarang:

```text
WhatsApp webhook
-> conversation saved
-> mode ai_first atau logic_ai
-> AI atau keyword
-> kalau gagal fallback manusia
-> lead detection
```

Kelemahan saat ini:

- Non-AI masih keyword-template.
- Tidak ada `knowledge_items`.
- Tidak ada structured retrieval.
- Tidak ada response composer.
- `knowledgeService` masih menyimpan satu JSON besar di `settings.product_knowledge`.

## Rencana Berikutnya

Ikuti `docs/ANSWER_ENGINE_PLAN.md`.

Start dari:

`Milestone 1 - Backend Foundation`

Urutan paling aman:

1. Tambah migration `knowledge_items`.
2. Buat `knowledgeItemService`.
3. Buat `intentService`.
4. Buat `retrievalService`.
5. Buat `answerEngineService`.
6. Tambah endpoint `POST /api/dashboard/answer-engine/test`.
7. Test tanpa mengubah webhook dulu.
8. Commit.

Jangan langsung rombak UI besar sebelum backend answer engine bisa dites dari API.

## Acceptance Untuk Milestone Berikutnya

Minimal harus bisa:

1. Insert beberapa `knowledge_items` manual lewat API atau seed sementara.
2. Test message:
   `halo kak paket A berapa dan bisa kirim ke Depok?`
3. Engine return:
   - intents multi
   - facts yang dipakai
   - missing fields
   - response deterministic
4. Jika data harga tidak ada, bot tidak mengarang harga.

## Commit History Yang Jadi Checkpoint

Terakhir yang relevan:

- `ad90b5a docs(bot): plan answer engine rebuild`
- `27897f2 feat(bot): improve reply pattern management`
- `5806285 feat(bot): add ready reply templates`
- `0d2a7df feat(ui): simplify bot setup`
- `848b128 feat(ui): simplify dashboard workflow`
- `5586a54 feat(ui): add workflow guide page`
- `71b4191 feat(ui): add branded dashboard login`

## Resume Checklist

Saat session baru:

1. Masuk VPS.
2. `cd /opt/leadbot`
3. `git status --short`
4. Baca `docs/SESSION_CONTEXT.md`
5. Baca `docs/ANSWER_ENGINE_PLAN.md`
6. Mulai dari milestone berikutnya yang belum ada commit.
7. Setelah perubahan:
   - `node --check` file JS
   - test endpoint
   - restart PM2 jika runtime berubah
   - `curl /api/health`
   - commit kecil
