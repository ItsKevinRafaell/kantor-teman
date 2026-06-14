# LeadBot API Documentation

Updated: 2026-06-14

LeadBot memakai Fonnte sebagai transport WhatsApp, AI owner-sales via 9router OpenAI-compatible, dan dashboard auth berbasis database. `DASHBOARD_EMAIL` + `DASHBOARD_PASSWORD` hanya menjadi bootstrap user pertama saat database masih kosong.

## Base URL

Production public bridge:

```text
https://autolead.kantorteman.my.id/api
```

Local/VPS app:

```text
http://127.0.0.1:3000/api
```

## Authentication

Dashboard API:

- Jika dashboard auth aktif, login lewat `/login`, atau pakai HTTP Basic Auth email/password untuk route `/api/dashboard/*`.
- Auth hanya boleh dimatikan dengan `DASHBOARD_AUTH_DISABLED=true` untuk lokal/staging tertutup. Jangan pakai mode ini untuk production publik.
- Reset password dashboard tersedia di `POST /api/auth/password/forgot` dan `POST /api/auth/password/reset`.
- SMTP production harus memakai sender `noreply@temanumkmkita.com`; secret hanya boleh ada di environment production.

KantorTeman bridge:

```text
X-KantorTeman-Key: <bridge-token>
Authorization: Bearer <bridge-token>
```

Fonnte webhook:

- Jika `FONNTE_WEBHOOK_SECRET` diset, webhook wajib membawa `x-webhook-secret`, `x-fonnte-webhook-secret`, query `secret`, atau body `secret`.

## Health

### GET `/api/health`

Mengecek app, rate limit, AI config, Fonnte config, dan jumlah eskalasi.

Response ringkas:

```json
{
  "status": "ok",
  "timestamp": "2026-06-14T00:00:00.000Z",
  "rateLimit": {},
  "ai": {},
  "whatsapp": { "provider": "fonnte", "configured": true },
  "fonnte": { "provider": "fonnte", "configured": true },
  "escalations": 0
}
```

## Dashboard

### GET `/api/dashboard/stats`

Statistik inbox, status AI, status Fonnte, jumlah eskalasi, dan jumlah realtime clients.

### GET `/api/dashboard/events`

Server-sent events untuk update realtime dashboard.

### GET `/api/dashboard/conversations`

Daftar percakapan aktif.

### GET `/api/dashboard/conversations/:id`

Detail pesan dalam satu percakapan.

### POST `/api/dashboard/conversations/:id/reply`

Kirim balasan manual lewat Fonnte. Setelah admin membalas, auto-reply AI untuk percakapan itu otomatis dipause.

```json
{
  "message": "Halo Kak, saya bantu cek dulu ya."
}
```

### POST `/api/dashboard/conversations/:id/auto-reply`

Pause atau resume auto-reply AI.

```json
{
  "paused": true
}
```

### POST `/api/dashboard/conversations/:id/escalate`

Tandai percakapan sebagai butuh admin.

```json
{
  "reason": "Pelanggan minta diskon khusus"
}
```

### POST `/api/dashboard/conversations/:id/close`

Tutup percakapan dan eskalasi aktif.

### GET `/api/dashboard/leads`

Daftar kandidat lead dari percakapan yang masuk pipeline.

### GET `/api/dashboard/whatsapp/status`

Status konfigurasi Fonnte. Endpoint ini hanya status konfigurasi; tidak ada QR, pairing, start, atau stop session di LeadBot.

## Knowledge

### GET `/api/dashboard/knowledge`

Ambil knowledge usaha dalam format object dan teks gabungan.

### PUT `/api/dashboard/knowledge`

Simpan knowledge manual.

### POST `/api/dashboard/knowledge/wizard`

Ganti data setup usaha dari wizard.

### GET `/api/dashboard/knowledge-items`

List item knowledge. Query yang tersedia: `type`, `q`, `active`.

### POST `/api/dashboard/knowledge-items`

Buat item knowledge baru.

### PUT `/api/dashboard/knowledge-items/setup`

Ganti semua item setup wizard.

### PUT `/api/dashboard/knowledge-items/:id`

Update satu item knowledge.

### DELETE `/api/dashboard/knowledge-items/:id`

Hapus satu item knowledge.

### GET `/api/dashboard/knowledge/uploads`

Daftar dokumen knowledge yang pernah diupload.

### POST `/api/dashboard/knowledge/upload`

Upload dokumen knowledge. Field form-data:

```text
file=<dokumen>
```

## AI Test

### POST `/api/dashboard/ai/test`

Uji jawaban AI owner-sales tanpa menunggu chat WhatsApp real.

```json
{
  "message": "Saya mau tanya harga paket website.",
  "history": []
}
```

## Fonnte Webhook

### POST `/api/webhook`

Endpoint inbound dari Fonnte. Bukan endpoint manual untuk operator.

Flow:

```text
Fonnte -> /api/webhook -> simpan inbound -> AI owner-sales -> Fonnte /send -> simpan outbound
```

Jika auto-reply sedang pause, inbound hanya disimpan dan AI tidak membalas.

## KantorTeman Bridge

### GET `/api/integrations/kantorteman/health`

Mengecek bridge dari KantorTeman ke AutoLead.

### POST `/api/integrations/kantorteman/whatsapp/send`

Mencatat atau mengirim pesan outbound dari KantorTeman.

```json
{
  "target": "6281234567890",
  "message": "Halo Kak, ini follow-up dari KantorTeman.",
  "contact_name": "Budi",
  "lead_id": 123,
  "campaign_id": "campaign-001",
  "dry_run": true
}
```

Catatan:

- Jika `KANTORTEMAN_BRIDGE_DEMO=true`, pesan hanya dicatat ke inbox dan tidak dikirim ke WhatsApp real.
- Jika `dry_run` atau `demo` bernilai `true`, request juga tidak mengirim WhatsApp real.
- Untuk kirim real, set `KANTORTEMAN_BRIDGE_DEMO=false`, pastikan `FONNTE_TOKEN` valid, lalu uji hanya ke nomor internal yang disetujui.

## Fonnte Send Adapter

Adapter memakai `POST https://api.fonnte.com/send` dengan header `Authorization` berisi token langsung, bukan `Bearer`. Parameter utama mengikuti dokumentasi Fonnte: `target`, `message`, `countryCode`, `connectOnly`, dan optional `inboxid`.

Referensi: https://docs.fonnte.com/api-send-message/

## Rate Limits

- Per nomor: mengikuti konfigurasi middleware runtime.
- Global: mengikuti konfigurasi middleware runtime.
