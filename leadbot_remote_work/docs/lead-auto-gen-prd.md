# PRD - Lead Auto Gen (WhatsApp Assistant Bot)
**Project:** WhatsApp Assistant Bot for KantorTeman UMKM
**Date:** 7 Juni 2026
**Status:** Planning
**Stack:** Self-hosted (VPS) + Fontee API
**Team:** Friday (PM + Dev) via Claude Code (VPS)
**Timeline:** ASAP

---

## 1. OBJECTIVE

Build automated WhatsApp lead generation system that:
- Captures leads via WhatsApp Business
- Auto-reply dengan keyword triggers
- Escalate ke manual takeover kalau bot ga mampu
- Log all conversations for analysis & training

---

## 2. CORE FEATURES (MVP)

### 2.1 Auto-Reply Engine
- **Greeting message** - Welcome + jam buka + lokasi + katalog link
- **Keyword triggers** - Respon otomatis based on keywords:
  - "harga" / "berapa" / "harganyа" → pricing info
  - "promo" / "diskon" / "sale" → promo aktive
  - "cara order" / "order" / "beli" → order guide
  - "alamat" / "lokasi" / "cara ke" → location info
- **Fallback** - Kalau keyword ga match → escalate

### 2.2 Manual Takeover System
- **Auto-escalation** - Bot confidence <70% → handoff ke admin
- **Notification** - Admin dapat notif (Telegram/Dashboard)
- **Seamless handoff** - Context transfer (last 10 messages)
- **Admin reply** - Reply langsung dari dashboard

### 2.3 Conversation Logging
- **Log all messages** - User, bot, admin messages
- **Session tracking** - Conversation ID, phone, timestamps
- **Status tracking** - bot | manual | resolved
- **Analytics base** - Data for future improvements

### 2.4 Dashboard Integration
- **View conversations** - Real-time active chats
- **Manual reply interface** - Send message as business
- **Takeover control** - Switch bot → manual mode
- **Metrics display** - Response time, resolution rate

---

## 3. NICE-TO-HAVE (Post-MVP)

- Product catalog integration (real-time dari backend)
- Order tracking via order number
- Sentiment detection (prioritas kalau customer kesel)
- Multi-account WhatsApp support
- Campaign broadcast

---

## 4. OUT OF SCOPE (v1)

- Payment gateway integration
- Voice/audio message handling
- Multi-language support
- AI-powered conversation (NLP/LLM)

---

## 5. USER FLOW

```
Customer → WhatsApp Message
    ↓
Bot check keyword/intent
    ↓
┌────────────────────────────────────┐
│ Match found?                       │
├──────────────┬─────────────────────┤
│ YES          │ NO                  │
│ ↓            │ ↓                   │
│ Bot reply    │ Check confidence    │
│ (greeting,   │ score               │
│  info,       │ ↓                   │
│  katalog)    │ <70%?               │
└──────────────┴─────────────────────┤
                    │               │
                   YES              NO
                    ↓               ↓
              Escalate          Auto-reply
              to admin          (fallback)
                    ↓
            Admin notified
                    ↓
            Admin takes over
                    ↓
            Conversation resolved
                    ↓
            Log saved
```

---

## 6. SUCCESS METRICS (KPIs)

| Metric | Target | Notes |
|--------|--------|-------|
| Response Time | <5 detik | Bot auto-reply |
| Auto-reply Success Rate | >60% | Bot handle majority |
| Manual Takeover Rate | <40% | Kalau >40%, bot ga efektif |
| CSAT | >4.0/5 | Post-chat survey |
| Cost per Conversation | <Rp 500 | API + agent time |

**Leading Indicators:**
- Keyword match accuracy
- Avg conversation length (semakin pendek = efisien)

---

## 7. INTEGRATION POINTS

### Fontee API
- Endpoint: send/receive WhatsApp messages
- Webhook: incoming messages listener
- Media handling: foto produk

### KantorTeman Backend
- Dashboard module: `/dashboard/whatsapp`
- API proxy: Fetch conversations
- Auth: Shared JWT/session

### VPS Infrastructure
- Bot backend: 24/7 running
- Database: PostgreSQL (logs)
- Process manager: PM2

---

## 8. RISKS & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|------------|
| WhatsApp ban | High | Multi-account rotation |
| Message queue overload | Medium | Rate limiting + Redis queue |
| Context loss on handoff | Medium | Store last 10 messages |
| Admin response time | Low | Push notification (Telegram) |

---

## 9. DEPENDENCIES

**External:**
- Fontee API credentials
- WhatsApp Business API approval
- VPS access (SSH keys)

**Internal:**
- KantorTeman repo access (for dashboard integration)
- Database schema design

---

## 10. ASSUMPTIONS

1. Fontee API supports webhook + send message endpoints
2. VPS has sufficient resources (2 vCPU, 2GB RAM)
3. WhatsApp Business API bisa di-approve (atau alternative)
4. Admin dashboard bisa di-build sebagai module KantorTeman

---

*Document by Friday (IT PM)*