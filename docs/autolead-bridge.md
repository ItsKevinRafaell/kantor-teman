# AutoLead Bridge Status

The old KantorTeman outbound WhatsApp bridge to AutoLead is deprecated.

Current policy:

- KantorTeman sends WhatsApp blast/follow-up/report notifications through Fonnte only.
- AutoLead may still hand qualified leads to KantorTeman through `/api/leads/external`.
- Do not configure AutoLead as KantorTeman's WhatsApp provider.

Use these Fonnte callbacks in production:

- Incoming replies: `/api/webhook/fonnte-incoming`
- Blast delivery/read/replied status: `/api/blast/webhook/fonnte`
