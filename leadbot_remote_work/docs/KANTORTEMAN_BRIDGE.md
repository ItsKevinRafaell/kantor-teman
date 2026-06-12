# KantorTeman Bridge

Bridge ini dipakai saat KantorTeman berjalan di shared hosting dan WAHA berjalan di VPS bersama AutoLead.

```text
KantorTeman shared hosting
-> public AutoLead Bridge
-> local WAHA container
-> WhatsApp
```

Endpoint:

- `GET /api/integrations/kantorteman/health`
- `POST /api/integrations/kantorteman/whatsapp/send`

Auth:

```http
X-KantorTeman-Key: <KANTORTEMAN_BRIDGE_TOKEN>
```

Jika `KANTORTEMAN_BRIDGE_TOKEN` kosong, app memakai `KANTORTEMAN_API_KEY`.

Demo mode:

```env
KANTORTEMAN_BRIDGE_DEMO=true
```

Saat demo mode aktif, request outbound dari KantorTeman akan disimpan ke tabel conversation/messages dengan responder `kantorteman_bridge`, tetapi tidak dikirim ke WhatsApp.
Tetap kirim payload demo dengan `dry_run: true` saat smoke test, supaya test tidak bergantung pada mode global.

Payload:

```json
{
  "target": "081234567890",
  "message": "Halo ...",
  "dry_run": true,
  "lead_id": 123,
  "campaign_id": "campaign-id",
  "business_name": "Nama Bisnis"
}
```

Public reverse proxy masih perlu disiapkan agar shared hosting bisa memanggil app ini. Target internal app:

```text
127.0.0.1:3000
```

## Smoke Test

Health check saja, tidak membuat conversation/message:

```bash
npm run smoke:kantorteman-bridge
```

Env minimal untuk smoke:

```env
AUTOLEAD_BRIDGE_URL=https://<public-autolead-domain>
KANTORTEMAN_BRIDGE_TOKEN=<bridge-token>
AUTOLEAD_SMOKE_SEND=false
```

Demo send hanya boleh dijalankan setelah approval eksplisit karena tetap mencatat pesan demo ke database AutoLead:

```env
AUTOLEAD_SMOKE_SEND=true
AUTOLEAD_SMOKE_TARGET=081234567890
```

Lalu jalankan:

```bash
npm run smoke:kantorteman-bridge
```

Expected demo result:

```json
{
  "step": "demo_send",
  "success": true,
  "action": "demo_recorded",
  "dryRun": true,
  "provider": "autolead_bridge"
}
```
