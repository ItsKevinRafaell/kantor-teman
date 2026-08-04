# Blueprint B — Agent Generate Carousel via officekantorteman

Status dokumen: SPEC (belum eksekusi). Dibuat 2026-08-04.
Ruang lingkup: officekantorteman (modul creative temanumkmkita), owner raka.

## 0. KOREKSI ASUMSI (penting — hasil audit codebase)
Asumsi awal: "officekantorteman = modul backend carousel generator, butuh wrapper office.py".
FAKTA dari `backend/routers/office.py`: officekantorteman itu **proxy ke Hermes gateway**.
Endpoint ERP `/api/office/*` cuma nerusin ke `HERMES_GATEWAY_URL/api/office/*`:
- `POST /api/office/chat/{profile}`  -> ngobrol ke agent Hermes (profile = raka dll)
- `GET  /api/office/status|history|timeline|conversations`
- `POST /api/office/agents` (admin)  -> CRUD agent
- catch-all proxy `/api/office/{path:path}` -> gateway.

KESIMPULAN: generate carousel BUKAN fitur backend ERP. Itu kerjaan AGENT HERMES (raka) yang
dipanggil dari dashboard officekantorteman. Jadi kita TIDAK perlu bikin office.py wrapper baru;
yang perlu: kasih agent raka KEMAMPUAN generate carousel end-to-end.

## 1. Alur yang Kevin mau (agent tiru cara kerja dia)
1. Brief design masuk (dari Kevin / dari chat officekantorteman).
2. Agent hit AI untuk generate desain DARI TEMPLATE yang sudah ada (mode carousel punya template2).
3. Agent olah template sendiri -> render jadi gambar.
4. Agent download hasil.
5. Agent kirim ke Telegram + kirim CAPTION juga.
Jadi agent handle: brief -> generate-dari-template -> render -> download -> kirim file+caption TG.

## 2. Yang perlu dipetakan dulu (unknowns — WAJIB dicek sebelum bangun)
1. TEMPLATE carousel itu bentuknya apa & tinggal di mana?
   - HTML/CSS template? Figma? JSON layout? Canva? File PSD?
   - Ada di frontend officekantorteman (belum ketemu di lokal) atau di storage (R2)?
   - AKSI: temukan repo/dir officekantorteman frontend. Cek "mode carousel" & folder template.
2. Render engine: gimana template jadi PNG jpg akhir?
   - Kalau HTML/CSS -> headless browser (Playwright/puppeteer) screenshot per slide.
   - Kalau ada API render existing -> pakai itu.
3. AI generate: model apa yang dipakai "hit AI untuk generate desain"?
   - Isi teks/copy carousel (LLM) vs generate image (image model)? Kemungkinan LLM isi copy ke
     slot template, bukan text-to-image penuh.
4. Kredensial Telegram buat kirim: agent raka sudah punya bot TG sendiri? (office.py env punya
   telegram_token per agent — kemungkinan sudah).

## 3. Rancangan (setelah unknowns terjawab)
Karena eksekusi ada di sisi agent Hermes raka, deliverable-nya berupa SKILL + script, bukan
endpoint backend. Rencana:

### Deliverable 1: skill `carousel-officekantorteman` untuk agent raka
Isi: langkah brief->pilih template->isi copy via AI->render->download->kirim TG+caption.
Plus pitfalls (ukuran slide IG 1080x1350, font, warna brand).

### Deliverable 2: script render carousel
`scripts/render_carousel.py`:
- Input: template_id + konten per slide (JSON) + brand.
- Proses: inject konten ke template HTML -> Playwright screenshot tiap slide -> PNG 1080x1350.
- Output: folder PNG + optional gabung jadi 1 file/zip.

### Deliverable 3: kirim ke Telegram
Agent pakai tool bawaan (send_message MEDIA:<path>) atau bot TG raka. Caption di message.
JANGAN auto-broadcast; kirim ke chat Kevin/officekantorteman untuk approve.

## 4. Konsistensi brand (dari memory Kevin)
Carousel officekantorteman: CLEAN LIGHT, aksen KUNING #FFC400 (BUKAN gold).
BENCI badge/chip kecil — buang. Desain dinilai dari MATA, bukan DOM. Kalau vision keblok,
JANGAN nambal grafis buta — tanya referensi vibe dulu.

## 5. Urutan eksekusi (kalau di-ACC)
1. TEMUKAN frontend officekantorteman + folder template carousel (unknown #1). Blocker utama.
2. Pahami format template + cara render existing (unknown #2,#3).
3. Bikin script render (Deliverable 2) — uji 1 template dulu.
4. Bungkus jadi skill agent raka (Deliverable 1) + jalur kirim TG (Deliverable 3).
5. Uji end-to-end: brief -> carousel PNG -> TG + caption.

## 6. Guardrail
- Kerjakan sebagai kit/branch terpisah yang gampang dibuang. JANGAN sentuh yang sudah di-ACC.
- Jangan nembak gelap desain; kalau ragu vibe, tanya referensi.
- Blocker #1 (lokasi template) harus ketemu dulu sebelum bangun apa pun.
