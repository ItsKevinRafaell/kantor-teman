# LeadBot Current Architecture

Updated: 2026-06-14

## Ringkasan

LeadBot adalah sistem WhatsApp sales assistant berbasis AI owner-sales.

Status runtime:

- Project VPS: `/opt/leadbot`
- App runtime: Node.js + Express
- Process manager: PM2 app `leadbot`
- Internal app port: `3000`
- Database: PostgreSQL
- Dashboard auth: aktif
- WhatsApp transport: Fonnte-only
- KantorTeman Bridge: aktif sebagai endpoint outbound; default demo mode mencatat pesan tanpa kirim WA real
- AI provider: 9router OpenAI-compatible

## Runtime Flow

### Inbound WhatsApp

```text
Fonnte webhook
-> POST /api/webhook
-> src/routes/webhook.js
-> fonnteService.parseWebhookPayload()
-> conversationService.getOrCreateConversation()
-> conversationService.addMessage(inbound)
-> aiService.generateSalesResponse()
-> fonnteService.sendMessage()
-> conversationService.addMessage(outbound)
-> conversationService.updateLeadInsights()
```

Jika conversation `auto_reply_paused = true`, inbound message hanya disimpan dan AI tidak membalas otomatis.

### Manual Reply

Manual reply dari dashboard:

```text
Dashboard inbox
-> POST /api/dashboard/conversations/:id/reply
-> conversationService.addMessage(outbound, responder=admin)
-> fonnteService.sendMessage()
-> conversationService.markHumanReply()
-> auto_reply_paused = true
```

Manual reply dari Telegram admin command `/reply` juga memakai Fonnte dan mem-pause AI untuk conversation tersebut.

### KantorTeman Outbound Bridge

```text
KantorTeman backend
-> HTTPS public AutoLead Bridge on VPS
-> POST /api/integrations/kantorteman/whatsapp/send
-> src/routes/webhook.js
-> conversationService.getOrCreateConversation()
-> conversationService.addMessage(outbound, responder=kantorteman_bridge)
-> if demo=false: fonnteService.sendMessage()
-> Fonnte API
```

Default production safety:

- `KANTORTEMAN_BRIDGE_DEMO=true` records only.
- Real send requires `KANTORTEMAN_BRIDGE_DEMO=false`, valid `FONNTE_TOKEN`, and internal-number smoke approval.

## Komponen Utama

### Express App

Entry point:

- `src/app.js`

Tanggung jawab:

- Load env
- Start Express server
- Run DB migration on boot
- Mount public dashboard
- Mount `/api` webhook/health routes
- Mount `/api/dashboard` dashboard API routes
- Start Telegram polling

### Webhook Route

File:

- `src/routes/webhook.js`

Endpoint:

- `GET /api/health`
- `POST /api/webhook`
- `GET /api/integrations/kantorteman/health`
- `POST /api/integrations/kantorteman/whatsapp/send`

Tanggung jawab:

- Terima webhook dari Fonnte
- Terima outbound request dari KantorTeman Bridge
- Abaikan message `fromMe`
- Simpan inbound message
- Jalankan AI owner-sales jika auto-reply tidak pause
- Kirim outbound via Fonnte
- Simpan lead stage dan score
- Buat external lead jika AI menilai lead cukup kuat

### Dashboard Route

File:

- `src/routes/dashboard.js`

Endpoint penting:

- `GET /api/dashboard/conversations`
- `GET /api/dashboard/conversations/:id`
- `POST /api/dashboard/conversations/:id/reply`
- `POST /api/dashboard/conversations/:id/auto-reply`
- `GET /api/dashboard/stats`
- `GET /api/dashboard/whatsapp/status`
- `POST /api/dashboard/knowledge/wizard`
- `POST /api/dashboard/knowledge/upload`
- `POST /api/dashboard/ai/test`

### Dashboard UI

File:

- `public/index.html`

View utama:

- Percakapan / live inbox
- Data Usaha wizard
- Dokumen upload
- AI Test

Dashboard tidak mengelola QR, pairing, start, atau stop session. Pairing device dilakukan di dashboard Fonnte.

### Fonnte Adapter

File:

- `src/services/fonnteService.js`

Tanggung jawab:

- Normalisasi payload webhook Fonnte
- Normalisasi nomor WhatsApp
- Kirim pesan via `POST https://api.fonnte.com/send`
- Laporkan status konfigurasi tanpa membuka token

Konfigurasi env:

- `FONNTE_TOKEN=<secret>`
- `FONNTE_BASE_URL=https://api.fonnte.com`
- `FONNTE_WEBHOOK_SECRET=<secret>`
- `FONNTE_COUNTRY_CODE=62`
- `FONNTE_CONNECT_ONLY=true`
- `FONNTE_TIMEOUT_MS=20000`

### AI Owner-Sales Engine

File:

- `src/services/aiService.js`

Provider AI wajib 9router OpenAI-compatible:

- `AI_BASE_URL`
- `AI_API_KEY`
- `AI_MODEL`

Default VPS: `AI_BASE_URL=http://127.0.0.1:20128/v1`.

Guardrail AI:

- Jangan mengarang harga, stok, promo, garansi, refund, alamat, SLA, diskon, atau janji layanan.
- Jika data kurang, jawab bagian aman lalu tanya 1 pertanyaan lanjutan.
- Jika kasus sensitif, set `needsAdmin = true`.

### Conversation Service

File:

- `src/services/conversationService.js`

Tanggung jawab:

- Create/get conversation
- Simpan message inbound/outbound
- Ambil active conversations
- Pause/resume AI per conversation
- Mark human reply
- Update lead stage dan score
- Dashboard stats

Channel default baru adalah `fonnte`. Migration mengubah data lama `channel='waha'` menjadi `fonnte`.

### Knowledge

Files:

- `src/services/knowledgeService.js`
- `src/services/knowledgeItemService.js`
- `src/services/documentKnowledgeService.js`

Sumber knowledge:

- Wizard dashboard
- Knowledge items
- Upload dokumen PDF/DOCX/DOC/TXT/MD

Upload dokumen memakai:

- `multer`
- `pdf-parse`
- `mammoth`

## Database Migration

File:

- `src/migrate.js`

Migration additive:

- Add conversation fields: `channel`, `auto_reply_paused`, `lead_stage`, `lead_score`, `last_ai_reason`, `last_human_reply_at`
- Set conversation channel default to `fonnte`
- Add message fields: `responder`, `message_type`, `external_id`, `metadata`
- Add `document_uploads`
- Ensure `knowledge_items`
- Ensure dashboard user and reset-token tables
- Insert setting `reply_engine = ai_owner_sales`

## Current Verification Target

Required checks after deploy:

- `node --check` on changed source files
- PM2 `leadbot` restart with `--update-env`
- `GET http://127.0.0.1:3000/api/health`
- `GET https://autolead.kantorteman.my.id/api/health`
- `GET /api/integrations/kantorteman/health` with bridge token
- Demo bridge send with `dry_run=true`
- Real Fonnte send only to internal test number after token rotation/update

## Removed Transport

LeadBot no longer contains local WhatsApp session/container management. The old Docker-based transport scripts, service file, dashboard QR/pairing UI, and session endpoints were removed.
