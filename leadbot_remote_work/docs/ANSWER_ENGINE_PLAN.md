# Answer Engine Plan

Dokumen ini adalah handoff utama untuk rombak LeadBot dari sistem "template statis" menjadi mesin jawaban yang bisa menyusun balasan dari data usaha. Kalau session terputus, baca dokumen ini dulu sebelum lanjut.

## Status Terakhir

- Repo VPS: `/opt/leadbot`
- App live: `http://202.6.204.179:20035/`
- PM2 app: `leadbot`
- Commit terakhir sebelum plan ini: `27897f2 feat(bot): improve reply pattern management`
- Mode aktif terakhir: `ai_first`
- Health terakhir: `GET /api/health` return `200`
- Knowledge saat audit masih default, belum ada data usaha real.
- `Pola Jawaban` sudah dirapikan UI-nya, tapi secara produk harus turun posisi menjadi `Aturan Khusus`.

## Masalah Yang Diselesaikan

Sistem sekarang masih terlalu statis:

- Keyword hanya memilih satu jawaban.
- Customer sering tanya beberapa hal dalam satu chat.
- Kalau dibuat 100 pola jawaban, admin UMKM akan bingung dan maintenance berat.
- `Info Usaha` sudah ada, tapi non-AI belum benar-benar memakainya sebagai sumber fakta.

Target baru:

```
WhatsApp masuk
-> Answer Engine
-> deteksi intent + ekstrak detail
-> ambil fakta dari knowledge base
-> susun jawaban
-> AI optional untuk polish/fallback
-> manusia hanya kalau data tidak cukup atau risiko salah
```

## Prinsip Produk

1. UMKM tidak boleh merasa sedang mengatur keyword teknis.
2. Admin cukup isi data usaha: produk, harga, lokasi, order, pembayaran, pengiriman, FAQ, dan batasan.
3. Bot harus bisa jawab beberapa pertanyaan dalam satu balasan.
4. Bot boleh bertanya 1 hal lanjutan kalau data kurang.
5. Bot tidak boleh mengarang harga, alamat, promo, stok, SLA, atau janji layanan.
6. `Pola Jawaban` hanya untuk override khusus, bukan otak utama.

## Arsitektur Target

### 1. Knowledge Base Terstruktur

Tambahkan table baru:

```sql
CREATE TABLE knowledge_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  type VARCHAR(50) NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  keywords TEXT[] DEFAULT '{}',
  metadata JSONB DEFAULT '{}'::jsonb,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_knowledge_items_type ON knowledge_items(type);
CREATE INDEX idx_knowledge_items_active ON knowledge_items(active);
CREATE INDEX idx_knowledge_items_keywords ON knowledge_items USING GIN(keywords);
```

Tipe awal:

- `business_profile`
- `product`
- `price`
- `promo`
- `order_flow`
- `payment`
- `shipping`
- `location`
- `business_hours`
- `policy`
- `faq`
- `bot_boundary`

Catatan: tetap simpan `settings.product_knowledge` untuk backward compatibility pada fase awal. Jangan langsung hapus.

### 2. Intent Detector

Buat file:

`src/services/intentService.js`

Output yang diharapkan:

```js
{
  intents: ['greeting', 'pricing', 'shipping', 'order'],
  slots: {
    productHints: ['paket a'],
    locationHints: ['depok'],
    quantity: null,
    dateHints: []
  },
  risk: 'normal',
  confidence: 0.82
}
```

Intent awal:

- `greeting`
- `product`
- `pricing`
- `promo`
- `stock`
- `order`
- `payment`
- `shipping`
- `location`
- `business_hours`
- `policy`
- `complaint`
- `unsubscribe`
- `handoff`
- `unknown`

Aturan penting:

- Satu pesan boleh punya banyak intent.
- Sapaan dan terima kasih tidak boleh mengalahkan intent bisnis.
- Complaint, refund, stop, unsubscribe harus bisa trigger eskalasi.

### 3. Knowledge Retriever

Buat file:

`src/services/retrievalService.js`

Tugas:

- Ambil `knowledge_items` sesuai intent.
- Cocokkan `title`, `content`, `keywords`, dan `metadata`.
- Untuk fase awal tidak perlu vector DB.
- Pakai scoring sederhana:
  - exact keyword match
  - type match sesuai intent
  - product/location hint match
  - active item only

Output:

```js
{
  facts: [
    { type: 'price', title: 'Paket A', content: 'Rp150.000', score: 91 },
    { type: 'shipping', title: 'Area Depok', content: 'Bisa kirim ke Depok 1-2 hari', score: 84 }
  ],
  missing: ['payment'],
  confidence: 0.78
}
```

### 4. Response Composer

Buat file:

`src/services/answerEngineService.js`

Tugas:

- Panggil `intentService.analyze(message, history)`.
- Panggil `retrievalService.retrieve(analysis, knowledge)`.
- Susun jawaban deterministic dari fakta.
- Kalau beberapa intent muncul, jawab beberapa poin sekaligus.
- Kalau data kurang, jawab yang ada lalu tanya 1 pertanyaan paling penting.
- Kalau risiko tinggi, return fallback manusia.

Output:

```js
{
  success: true,
  response: 'Halo kak. Paket A harganya Rp150.000. Untuk Depok bisa dikirim 1-2 hari. Kalau mau order, kakak bisa kirim nama, alamat, dan jumlah pesanan ya.',
  responder: 'answer_engine',
  confidence: 0.84,
  needsHuman: false,
  analysis: { ... },
  facts: [ ... ],
  missing: []
}
```

Jika tidak cukup data:

```js
{
  success: true,
  response: 'Bisa kak. Untuk harga saya perlu tahu produk atau layanan yang kakak maksud dulu. Kakak tertarik yang mana ya?',
  responder: 'answer_engine',
  confidence: 0.52,
  needsHuman: false,
  missing: ['product']
}
```

Jika risiko salah:

```js
{
  success: false,
  needsHuman: true,
  reason: 'Pertanyaan sensitif atau data tidak tersedia'
}
```

### 5. Webhook Flow Baru

File yang perlu diubah:

`src/routes/webhook.js`

Flow target:

```js
if (escalationService.shouldEscalate(message)) -> human

answer = await answerEngineService.generate(message, leadContext)
if answer.success && !answer.needsHuman -> sendAutoReply(answer.response, 'answer_engine')

if mode allows AI:
  ai = await tryAi(...)
  if ai success -> sendAutoReply(ai.response, 'ai')

keyword = await tryKeyword(...)
if keyword -> sendAutoReply(keyword.response, 'keyword_override')

human fallback
```

Catatan:

- Keyword menjadi fallback override, bukan primary brain.
- Untuk mode `ai_first`, tetap boleh AI dulu jika user mau, tapi rekomendasi produk adalah mode baru: `engine_ai`.
- Jangan hapus mode lama sampai flow baru stabil.

### 6. Dashboard UI Baru

File yang perlu diubah:

`public/index.html`

Ubah menu `Info Usaha` menjadi wizard yang lebih operasional:

1. `Profil Usaha`
2. `Produk & Harga`
3. `Promo`
4. `Cara Order`
5. `Pembayaran`
6. `Pengiriman / Area Layanan`
7. `FAQ`
8. `Batasan Bot`
9. `Aturan Khusus`

Tujuan UX:

- User UMKM tidak melihat "keyword management" sebagai pekerjaan utama.
- Ada checklist kesiapan bot berdasarkan isi knowledge items.
- Ada tombol "Tes Pertanyaan" yang menampilkan:
  - jawaban bot
  - intent terdeteksi
  - data yang dipakai
  - data yang belum lengkap

### 7. API Dashboard Baru

File yang perlu diubah:

`src/routes/dashboard.js`

Endpoint baru:

- `GET /api/dashboard/knowledge-items`
- `POST /api/dashboard/knowledge-items`
- `PUT /api/dashboard/knowledge-items/:id`
- `DELETE /api/dashboard/knowledge-items/:id`
- `POST /api/dashboard/answer-engine/test`
- `POST /api/dashboard/knowledge/import-legacy`

Legacy import:

- Ambil `settings.product_knowledge`
- Pecah menjadi `knowledge_items`
- Simpan tanpa menghapus data lama

### 8. KantorTeman Sync

File terkait:

- `src/services/knowledgeService.js`
- `src/services/kantortemanService.js`

Target:

- Sync dari API KantorTeman masuk ke `knowledge_items`.
- Mapping fleksibel dari response:
  - products/services -> `product`
  - price/pricing/packages -> `price`
  - faq/faqs -> `faq`
  - workflow/process/cara_kerja -> `order_flow`
  - payment -> `payment`
  - shipping/delivery/area -> `shipping`

Jangan request ke KantorTeman sampai semua flow lokal stabil, sesuai instruksi user sebelumnya.

## Milestone Eksekusi

### Milestone 1 - Backend Foundation

Files:

- `src/migrate.js`
- `src/services/knowledgeItemService.js`
- `src/services/intentService.js`
- `src/services/retrievalService.js`
- `src/services/answerEngineService.js`
- `src/routes/dashboard.js`

Tasks:

1. Tambah migration `knowledge_items`.
2. Buat CRUD service.
3. Buat intent detector rule-based.
4. Buat retriever rule-based.
5. Buat composer awal.
6. Tambah endpoint test.

Acceptance:

- `node --check` semua file baru lolos.
- `POST /api/dashboard/answer-engine/test` bisa jawab tanpa AI.
- Knowledge default kosong tetap tidak crash.

### Milestone 2 - Webhook Integration

Files:

- `src/routes/webhook.js`
- `src/services/modeService.js`

Tasks:

1. Integrasikan `answerEngineService`.
2. Tambah responder `answer_engine`.
3. Tambah mode baru jika perlu: `engine_ai`.
4. Pastikan fallback manusia tetap jalan.

Acceptance:

- Pesan campuran bisa dijawab multi-intent.
- AI off tetap bisa jawab dari knowledge.
- Kalau knowledge kosong, bot tanya klarifikasi atau fallback aman.

### Milestone 3 - Dashboard Knowledge UX

Files:

- `public/index.html`
- `src/routes/dashboard.js`

Tasks:

1. Tambah UI wizard knowledge.
2. Tambah CRUD knowledge item.
3. Tambah readiness score dari `knowledge_items`.
4. Ubah `Pola Jawaban` menjadi `Aturan Khusus`.
5. Tambah panel test jawaban dengan debug sederhana.

Acceptance:

- UMKM bisa isi produk/harga/order tanpa menyentuh keyword.
- Test jawaban menunjukkan data yang dipakai.
- UI tetap light/dark, Poppins, primary kuning tidak berlebihan.

### Milestone 4 - Legacy Migration

Files:

- `src/services/knowledgeService.js`
- `src/routes/dashboard.js`

Tasks:

1. Import `settings.product_knowledge` ke `knowledge_items`.
2. Convert businessInfo textarea menjadi beberapa item.
3. Tetap support format lama untuk AI prompt sementara.

Acceptance:

- Data lama tidak hilang.
- `knowledgeToText()` bisa membaca gabungan legacy + knowledge items.

### Milestone 5 - KantorTeman Sync

Files:

- `src/services/knowledgeService.js`
- `src/services/kantortemanService.js`
- `src/routes/dashboard.js`

Tasks:

1. Tambah sync endpoint ke `knowledge_items`.
2. Mapping response KantorTeman.
3. Tambah error summary yang mudah dibaca admin.

Acceptance:

- Sync tidak merusak data manual.
- Kalau API gagal, UI menampilkan alasan jelas.

## Test Cases Wajib

### Multi Intent

Input:

`halo kak paket A berapa dan bisa kirim ke Depok?`

Expected:

- Intent: greeting, pricing, shipping
- Jawaban menyapa, jawab harga kalau ada, jawab pengiriman kalau ada.

### Data Kurang

Input:

`harganya berapa kak?`

Expected:

- Bot tanya produk/layanan yang dimaksud.
- Tidak mengarang harga.

### Order

Input:

`saya mau order 10 pcs untuk besok`

Expected:

- Intent order.
- Ambil cara order.
- Minta detail kurang seperti produk/alamat jika belum ada.

### Payment

Input:

`bisa bayar pakai qris atau transfer?`

Expected:

- Jawab metode pembayaran dari knowledge.
- Kalau belum ada, tanya atau fallback aman.

### Complaint / Stop

Input:

`stop jangan chat saya lagi`

Expected:

- Eskalasi / jangan auto-sales agresif.

## File Yang Tidak Boleh Disentuh

- Jangan sentuh project lokal `/home/kevin/kantorteman`.
- Jangan ubah project KantorTeman.
- Fokus hanya VPS `/opt/leadbot`.

## Command Penting

SSH:

```bash
rtk env SSHPASS='AmKeBFT23Ejy' sshpass -e ssh -o StrictHostKeyChecking=no root@202.6.204.179 -p 20033 'cd /opt/leadbot && ...'
```

Restart:

```bash
rtk env SSHPASS='AmKeBFT23Ejy' sshpass -e ssh -o StrictHostKeyChecking=no root@202.6.204.179 -p 20033 'cd /opt/leadbot && pm2 restart leadbot --update-env'
```

Health:

```bash
rtk curl -sS http://202.6.204.179:20035/api/health
```

Dashboard API:

```bash
rtk curl -sS -u 'admin:W4Erq8GO2Zc0h0bIqP' http://202.6.204.179:20035/api/dashboard/knowledge
```

## Resume Checklist Untuk Next Session

1. SSH ke VPS.
2. `cd /opt/leadbot`
3. `git status --short`
4. `git log --oneline -5`
5. Baca dokumen ini.
6. Jika belum ada commit setelah dokumen ini, mulai dari Milestone 1.
7. Setelah setiap milestone:
   - `node --check` file JS yang diubah
   - test endpoint terkait
   - `pm2 restart leadbot --update-env`
   - `curl /api/health`
   - commit dengan pesan jelas

## Commit Strategy

Commit kecil per milestone:

- `feat(knowledge): add structured knowledge items`
- `feat(bot): add rule-based answer engine`
- `feat(bot): route webhook through answer engine`
- `feat(ui): add knowledge setup wizard`
- `feat(knowledge): import legacy business info`
- `feat(knowledge): sync items from KantorTeman`

## Keputusan Belum Final

1. Mode default nanti:
   - rekomendasi: `engine_ai`
   - fallback: `answer_engine -> ai -> keyword -> human`

2. Full vector RAG:
   - jangan sekarang.
   - evaluasi setelah structured knowledge + rule retrieval stabil.

3. UI debug intent:
   - tampil di test panel saja.
   - jangan tampil di percakapan customer.
