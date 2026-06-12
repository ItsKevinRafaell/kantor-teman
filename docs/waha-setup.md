# WAHA Setup for Kantor Teman

Goal: use one WhatsApp number for two apps without fighting over the device session.

- AutoLead owns CS bot behavior: incoming message handling, auto-reply, human handoff.
- Kantor Teman uses AutoLead Bridge for production outreach when it runs outside the VPS.
- Do not pair the same WhatsApp number into two different WAHA/Fonnte/device sessions at the same time.

For shared-hosting production, read [autolead-bridge.md](autolead-bridge.md). Direct WAHA provider is only appropriate when Kantor Teman can reach the WAHA container URL.

## WAHA Server

Official docs:

- Quick start: https://waha.devlike.pro/docs/overview/quick-start/
- Sessions API: https://waha.devlike.pro/docs/how-to/sessions/
- Send messages: https://waha.devlike.pro/docs/how-to/send-messages/
- Events and webhooks: https://waha.devlike.pro/docs/how-to/events/
- Security: https://waha.devlike.pro/docs/how-to/security/

Minimum flow:

1. Run WAHA with Docker and generate credentials using the official `init-waha` flow.
2. Open WAHA Dashboard.
3. Start one session, usually `default`.
4. Scan the QR using the WhatsApp number shared by AutoLead and Kantor Teman.
5. Keep `WAHA_API_KEY` private. Kantor Teman sends it as `X-Api-Key`.

WAHA send API used by Kantor Teman:

```http
POST /api/sendText
X-Api-Key: <waha_api_key>

{
  "session": "default",
  "chatId": "6281234567890@c.us",
  "text": "Halo ..."
}
```

## Kantor Teman Settings for Direct WAHA

Use this only when Kantor Teman backend can reach the WAHA container directly.

Open `Settings -> Integrasi -> WhatsApp Provider`:

- Provider Aktif: `WAHA`
- WAHA Base URL: internal WAHA URL, for example `http://127.0.0.1:3000`
- WAHA Session: `default`
- WAHA API Key: plain API key used in the `X-Api-Key` header
- WAHA Webhook Secret: same HMAC secret configured in WAHA webhook config
- Delay Blast per Pesan: keep conservative, start at `5` seconds or higher

Equivalent backend settings/env names:

```env
WHATSAPP_PROVIDER=waha
WAHA_BASE_URL=http://127.0.0.1:3000
WAHA_API_KEY=change-me
WAHA_SESSION=default
WAHA_WEBHOOK_SECRET=change-me
WHATSAPP_BLAST_DELAY_SECONDS=5
```

## Webhook Routing

Kantor Teman exposes:

- `POST /api/webhook/waha`
- `POST /api/blast/webhook/waha`

Use either URL. They point to the same handler.

Recommended WAHA events for Kantor Teman:

- `message`: mark lead as replied and handle opt-out terms
- `message.ack`: update delivered/read tracking when the engine emits ack events

Recommended WAHA webhook security:

- Set `hmac.key` in the WAHA session webhook config.
- Put the same value in Kantor Teman `waha_webhook_secret`.
- WAHA sends `X-Webhook-Hmac` using sha512 over the raw request body.

If AutoLead is the primary CS bot and Kantor Teman is on shared hosting, use AutoLead Bridge instead of direct WAHA. AutoLead should be the first consumer of incoming messages.

## Safe Rollout

1. Keep Fonnte token configured as fallback.
2. Pair WAHA session and verify WAHA Dashboard status is connected.
3. Save WAHA settings in Kantor Teman and click `Test Koneksi WAHA`.
4. Send one manual WA from a test lead.
5. Run a tiny blast batch of 1-3 internal numbers.
6. Confirm `BlastMessage` status changes to `sent`, and replies update lead status to `Replied`.
7. Only then switch real campaign batches to WAHA.

Rollback is simple: change Provider Aktif back to `Fonnte`.
