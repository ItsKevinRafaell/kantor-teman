# LeadBot Current Architecture

Updated: 2026-06-11 10:24 WIB.

## Ringkasan

LeadBot sekarang diarahkan menjadi sistem WhatsApp sales assistant berbasis AI owner-sales. Sistem lama berbasis Fonnte, keyword matching, mode switching, dan deterministic answer engine sudah dikeluarkan dari source runtime.

Status runtime saat checkpoint ini:
- Project VPS: `/opt/leadbot`
- App runtime: Node.js + Express
- Process manager: PM2 app `leadbot`
- Internal app port: `3000`
- Database: PostgreSQL
- Dashboard auth: aktif
- WhatsApp target transport: WAHA
- WAHA container runtime: belum aktif karena image belum dipull
- WAHA system scaffold: sudah disiapkan
- KantorTeman Bridge: aktif sebagai demo endpoint untuk mencatat outbound dari KantorTeman tanpa kirim WA real
- Docker: sudah terpasang dan aktif
- Storage VPS: sekitar 3.7 GB free dari 9.8 GB total

## Runtime Flow

### Inbound WhatsApp

Target flow setelah WAHA container aktif:

```text
WhatsApp
-> WAHA container
-> POST http://host.docker.internal:3000/api/webhook
-> src/routes/webhook.js
-> wahaService.parseWebhookPayload()
-> conversationService.getOrCreateConversation()
-> conversationService.addMessage(inbound)
-> aiService.generateSalesResponse()
-> wahaService.sendMessage()
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
-> wahaService.sendMessage()
-> conversationService.markHumanReply()
-> auto_reply_paused = true
```

Manual reply dari Telegram admin command `/reply` juga memakai WAHA dan mem-pause AI untuk conversation tersebut.

### KantorTeman Outbound Bridge

Flow production saat KantorTeman berada di shared hosting:

```text
KantorTeman backend
-> HTTPS public AutoLead Bridge on VPS
-> POST /api/integrations/kantorteman/whatsapp/send
-> src/routes/webhook.js
-> conversationService.getOrCreateConversation()
-> conversationService.addMessage(outbound, responder=kantorteman_bridge)
-> if demo=false: wahaService.sendMessage()
-> WAHA local VPS
```

Status saat ini:
- Endpoint bridge sudah aktif di app AutoLead.
- Default demo mode: `KANTORTEMAN_BRIDGE_DEMO=true`.
- Karena WAHA image/container belum aktif, bridge hanya menyimpan outbound message ke inbox/conversation.
- Setelah WAHA aktif dan paired, set `KANTORTEMAN_BRIDGE_DEMO=false` untuk kirim real.

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
- Terima webhook dari WAHA
- Terima outbound request dari KantorTeman Bridge
- Abaikan message `fromMe`
- Simpan inbound message
- Jalankan AI owner-sales jika auto-reply tidak pause
- Kirim outbound via WAHA
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
- `GET /api/dashboard/whatsapp/session`
- `POST /api/dashboard/whatsapp/start`
- `POST /api/dashboard/whatsapp/stop`
- `GET /api/dashboard/whatsapp/qr`
- `POST /api/dashboard/whatsapp/pairing-code`
- `POST /api/dashboard/knowledge/wizard`
- `POST /api/dashboard/knowledge/upload`
- `POST /api/dashboard/ai/test`

Endpoint teknis lama untuk mode/keyword/answer-engine sudah dihapus dari dashboard route.

### Dashboard UI

File:
- `public/index.html`

View utama:
- Percakapan / live inbox
- Data Usaha wizard
- Dokumen upload
- AI Test
- WhatsApp session setup

UI lama yang mengelola mode, keyword trigger, regex, priority, dan pola jawaban tidak lagi menjadi bagian dashboard utama.

### AI Owner-Sales Engine

File:
- `src/services/aiService.js`

Tanggung jawab:
- Bangun prompt owner-sales
- Ambil knowledge aktif
- Ambil riwayat chat
- Panggil provider AI via adapter
- Parse output JSON dari AI
- Return:
  - `response`
  - `leadStage`
  - `leadScore`
  - `confidence`
  - `needsAdmin`
  - `reason`

Provider AI sekarang wajib 9router OpenAI-compatible:
- `AI_PROVIDER`
- `AI_ENDPOINT_STYLE`
- `AI_BASE_URL`
- `AI_API_KEY`
- `AI_MODEL`

Default VPS: `AI_BASE_URL=http://127.0.0.1:20128/v1`.
Default akses luar VPS: `http://9router.kantorteman.my.id/v1` setelah Cloudflare route aktif.

Guardrail AI:
- Jangan mengarang harga, stok, promo, garansi, refund, alamat, SLA, diskon, atau janji layanan.
- Jika data kurang, jawab bagian aman lalu tanya 1 pertanyaan lanjutan.
- Jika kasus sensitif, set `needsAdmin = true`.

### WAHA Adapter

File:
- `src/services/wahaService.js`

Tanggung jawab:
- Normalisasi payload webhook WAHA
- Normalisasi phone/chatId
- Kirim text via `POST /api/sendText`
- Cek session status
- Start/stop session
- Ambil QR
- Request pairing code

Konfigurasi env:
- `WAHA_BASE_URL=http://127.0.0.1:3001`
- `WAHA_SESSION=default`
- `WAHA_API_KEY=<secret>`
- `WAHA_WEBHOOK_SECRET=<secret>`

### KantorTeman Bridge Config

Config source:
- `src/config.js`

Env:
- `KANTORTEMAN_BRIDGE_TOKEN=<secret>`
- `KANTORTEMAN_BRIDGE_DEMO=true`

Fallback:
- Jika `KANTORTEMAN_BRIDGE_TOKEN` kosong, app memakai `KANTORTEMAN_API_KEY`.

Auth header untuk request dari KantorTeman:
- `X-KantorTeman-Key: <secret>`

Public reverse proxy masih perlu disiapkan sebelum shared hosting bisa memanggil bridge.

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

Field penting di `conversations`:
- `auto_reply_paused`
- `lead_stage`
- `lead_score`
- `last_ai_reason`
- `last_human_reply_at`
- `channel`

Field penting di `messages`:
- `responder`
- `message_type`
- `external_id`
- `metadata`

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

Dokumen yang diproses masuk ke:
- `document_uploads`
- `knowledge_items`

## WAHA System Scaffold

Docker sudah terpasang, tetapi container WAHA belum running karena image belum bisa dipull dengan storage saat ini.

Files:
- `scripts/waha-pull.sh`
- `scripts/waha-run.sh`
- `scripts/leadbot-waha.service`
- `/etc/systemd/system/leadbot-waha.service`
- `docs/WAHA_SYSTEM_SETUP.md`

Service status saat checkpoint:
- `leadbot-waha.service`: loaded, disabled, inactive

Script behavior:
- `scripts/waha-pull.sh` menolak pull jika free disk di bawah `WAHA_MIN_FREE_KB`.
- Default minimum free disk: 5 GB.
- `scripts/waha-run.sh` menolak start jika image WAHA belum ada.

Target WAHA runtime setelah storage dinaikkan:

```text
Docker image: devlikeapro/waha:noweb
Container: leadbot-waha
Host port: 127.0.0.1:3001
Container port: 3000
Session dir: /opt/leadbot/.waha/.sessions
Media dir: /opt/leadbot/.waha/.media
Webhook URL: http://host.docker.internal:3000/api/webhook
Webhook events: message
```

Commands setelah storage dinaikkan:

```bash
cd /opt/leadbot
scripts/waha-pull.sh
systemctl enable --now leadbot-waha.service
systemctl status leadbot-waha.service --no-pager
curl -sS http://127.0.0.1:3001/api/sessions
```

## Sistem Lama Yang Sudah Dihapus Dari Source

Files removed:
- `src/services/fonnteService.js`
- `src/services/keywordService.js`
- `src/services/keywordTemplates.js`
- `src/services/modeService.js`
- `src/services/answerEngineService.js`
- `src/services/intentService.js`
- `src/services/retrievalService.js`

Referensi berikut sudah tidak ditemukan di `src`, `public`, dan `package.json`:
- `fonnteService`
- `keywordService`
- `modeService`
- `answerEngineService`
- `intentService`
- `retrievalService`

Catatan:
- Tabel database lama seperti `keywords` tidak didrop agar rollback historis tetap mungkin.
- Source runtime tidak lagi memakai tabel/engine tersebut.

## Database Migration

File:
- `src/migrate.js`

Migration additive yang sudah dijalankan:
- Add conversation fields:
  - `channel`
  - `auto_reply_paused`
  - `lead_stage`
  - `lead_score`
  - `last_ai_reason`
  - `last_human_reply_at`
- Add message fields:
  - `responder`
  - `message_type`
  - `external_id`
  - `metadata`
- Add `document_uploads`
- Ensure `knowledge_items`
- Insert setting `reply_engine = ai_owner_sales`

## Current Verification

Verified on 2026-06-11 WIB:
- PM2 app `leadbot` online.
- App listening on internal port `3000`.
- `GET http://127.0.0.1:3000/api/health` returns OK.
- Docker installed and active.
- `leadbot-waha.service` exists but is disabled/inactive.
- WAHA image/container not present.
- Old engine service references are clean.

## Known Pending Work

Pending until storage upgrade:
- Pull `devlikeapro/waha:noweb`
- Start `leadbot-waha.service`
- Login WhatsApp via QR/pairing code
- Validate WAHA session status
- Validate real inbound WhatsApp webhook
- Validate outbound WAHA send
- Siapkan public hostname/reverse proxy untuk AutoLead Bridge agar KantorTeman shared hosting bisa mengakses VPS

Recommended storage before WAHA runtime:
- Minimum practical: 15 GB total disk
- Safer: 20 GB total disk
- Keep at least 5 GB free before pulling WAHA image

## Rollback Notes

Remote backup before WAHA/AI rewrite:
- `/opt/leadbot/backups/pre-waha-ai-20260611-011254.patch`
- `/opt/leadbot/backups/pre-waha-ai-20260611-011254.status.txt`
- `/opt/leadbot/backups/pre-waha-ai-20260611-011254.diffstat.txt`

Rollback outline:

```bash
cd /opt/leadbot
cp backups/pre-waha-ai-20260611-011254.patch /tmp/pre-waha-ai.patch
git apply -R /tmp/pre-waha-ai.patch
npm install --no-audit --no-fund
node src/migrate.js
pm2 restart leadbot --update-env
```

If WAHA service has been started later:

```bash
systemctl disable --now leadbot-waha.service
docker rm -f leadbot-waha
```
