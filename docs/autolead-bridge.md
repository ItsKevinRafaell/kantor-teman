# AutoLead Bridge Integration

Use this when KantorTeman and WAHA are not on the same machine.

Production target:

```text
KantorTeman shared hosting
-> HTTPS AutoLead Bridge on VPS
-> local WAHA container on VPS
-> WhatsApp device session
```

KantorTeman should not call `127.0.0.1:3001` WAHA in production because `127.0.0.1` would point to shared hosting, not the VPS.

## AutoLead VPS

Project:

- Remote path: `/opt/leadbot`
- Runtime: Node.js Express via PM2 app `leadbot`
- Internal app port: `3000`
- Future WAHA local port: `127.0.0.1:3001`

Bridge endpoints added:

- `GET /api/integrations/kantorteman/health`
- `POST /api/integrations/kantorteman/whatsapp/send`

Auth header:

```http
X-KantorTeman-Key: <bridge-token>
```

For demo, AutoLead runs with `KANTORTEMAN_BRIDGE_DEMO=true`, so `POST /whatsapp/send` records the outbound message into AutoLead conversations but does not call WAHA.

## KantorTeman Settings

Use `Settings -> Integrasi -> WhatsApp Provider`:

- Provider Aktif: `AutoLead Bridge`
- AutoLead Bridge Base URL: public VPS URL, for example `https://leadbot.example.com`
- AutoLead Bridge Token: same value as AutoLead `KANTORTEMAN_BRIDGE_TOKEN`
- Mode Demo AutoLead: on until WAHA container is pulled and paired

Env names supported by KantorTeman:

```env
WHATSAPP_PROVIDER=autolead
AUTOLEAD_BASE_URL=https://leadbot.example.com
AUTOLEAD_API_KEY=change-me
AUTOLEAD_DEMO=true
```

Payload sent by KantorTeman:

```json
{
  "target": "081234567890",
  "message": "Halo ...",
  "dry_run": true,
  "lead_id": 123,
  "campaign_id": "campaign-id",
  "template_id": "template-id",
  "batch_name": "Batch Name",
  "business_name": "Nama Bisnis"
}
```

Demo success response:

```json
{
  "success": true,
  "action": "demo_recorded",
  "provider": "autolead_bridge",
  "dryRun": true
}
```

## Public URL Requirement

The VPS app currently listens internally on port `3000`. A public reverse proxy is still required before shared hosting can call it.

Recommended Caddy target:

```caddy
leadbot.example.com {
  reverse_proxy 127.0.0.1:3000
}
```

After DNS/reverse proxy is ready:

```bash
curl -H "X-KantorTeman-Key: $KANTORTEMAN_BRIDGE_TOKEN" \
  https://leadbot.example.com/api/integrations/kantorteman/health
```

## Rollout

1. Keep AutoLead demo mode on.
2. Set KantorTeman provider to `AutoLead Bridge`.
3. Send one manual WA from a test lead.
4. Confirm it appears in AutoLead conversation inbox as outbound `kantorteman_bridge`.
5. Pull and pair WAHA on the VPS.
6. Set AutoLead `KANTORTEMAN_BRIDGE_DEMO=false`.
7. Send a tiny real batch before normal blast volume.

## Two-Way Sync Coverage

Verified integration paths:

- KantorTeman outbound WA/blast/follow-up -> AutoLead Bridge -> AutoLead conversation inbox.
- AutoLead high-intent WhatsApp lead -> `POST /api/leads/external` on KantorTeman.
- AutoLead AI metadata sent to KantorTeman external lead payload:
  - `lead_stage`
  - `lead_score`
  - `ai_reason`
  - `conversation_id`
- KantorTeman stores AutoLead AI context as `LeadAnalysis`.
- KantorTeman creates an in-app notification for AutoLead prospects.

Not synced as a shared object:

- AutoLead conversation history remains in AutoLead dashboard.
- AutoLead escalation rows remain in AutoLead dashboard and Telegram flow.
- KantorTeman receives the qualified prospect/lead handoff, AI score/stage/reason, and an in-app notification.
