# WhatsApp Provider Policy

KantorTeman no longer supports WAHA as a WhatsApp transport.

Production WhatsApp sending and callbacks use Fonnte only:

- Outbound send: `https://api.fonnte.com/send`
- Incoming webhook: `/api/webhook/fonnte-incoming`
- Blast status webhook: `/api/blast/webhook/fonnte`

Keep the Fonnte token in production settings/DB only. Do not commit tokens to source files or docs.
