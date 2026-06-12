# SPRINT PLAN - Lead Auto Gen (WhatsApp Assistant Bot)
**Project:** Lead Auto Gen
**Start:** 7 Juni 2026
**Duration:** 4 weeks (MVP)
**Team:** Friday (PM + Dev) via Claude Code

---

## SPRINT OVERVIEW

```
Week 1: Foundation        → Infrastructure + Basic Bot
Week 2: Core Features     → Keyword Engine + Dashboard
Week 3: Integration       → KantorTeman Integration + Testing
Week 4: Polish + Launch  → Bug Fixes + Documentation + Beta
```

---

## SPRINT 1: FOUNDATION (Day 1-5)

### Goal: VPS setup + Basic Bot working

**Tasks:**

| # | Task | Type | Est. Time | Priority |
|---|------|------|-----------|----------|
| 1.1 | Provision VPS LXC container (Node.js 20 + PostgreSQL 16) | Infra | 2h | P0 |
| 1.2 | Setup PM2 process manager | Infra | 1h | P0 |
| 1.3 | Install & configure Fontee API SDK | Integration | 2h | P0 |
| 1.4 | Build basic message handler (receive + echo) | Dev | 3h | P0 |
| 1.5 | Setup webhook listener for incoming messages | Dev | 2h | P0 |
| 1.6 | Basic database schema (conversations, messages) | DB | 2h | P0 |
| 1.7 | Test send/receive via Fontee API | Testing | 2h | P0 |

**Deliverables:**
- ✅ VPS ready with Node.js + PostgreSQL
- ✅ Basic bot can receive and send messages
- ✅ Database schema created

**Definition of Done:**
- Bot responds to any message with "Hello, this is a test"
- Messages stored in database

---

## SPRINT 2: CORE FEATURES (Day 6-10)

### Goal: Keyword engine + Dashboard MVP

**Tasks:**

| # | Task | Type | Est. Time | Priority |
|---|------|------|-----------|----------|
| 2.1 | Build keyword matching engine | Dev | 4h | P0 |
| 2.2 | Implement auto-reply templates (greeting, harga, promo, order) | Dev | 3h | P0 |
| 2.3 | Build confidence scoring (match → reply, no-match → escalate) | Dev | 3h | P0 |
| 2.4 | Create admin notification system (Telegram webhook) | Dev | 2h | P0 |
| 2.5 | Build conversation history view (simple HTML) | Dev | 3h | P1 |
| 2.6 | Build admin reply interface (send message as business) | Dev | 3h | P1 |
| 2.7 | Implement handoff context transfer (last 10 messages) | Dev | 2h | P0 |
| 2.8 | Basic metrics display (auto-reply rate, response time) | Dev | 2h | P2 |

**Deliverables:**
- ✅ Keyword engine responds correctly
- ✅ Dashboard shows conversations + admin reply
- ✅ Escalation flow works

**Definition of Done:**
- Customer: "harga produk X" → Bot replies with pricing info
- Customer: "satu dua tiga empat lima" (no keyword) → Escalates to admin
- Admin receives Telegram notification
- Admin can reply from dashboard

---

## SPRINT 3: INTEGRATION (Day 11-15)

### Goal: KantorTeman integration + E2E testing

**Tasks:**

| # | Task | Type | Est. Time | Priority |
|---|------|------|-----------|----------|
| 3.1 | Design API contract (Bot ↔ KantorTeman) | Design | 2h | P0 |
| 3.2 | Build REST API for dashboard integration | Dev | 4h | P0 |
| 3.3 | Implement JWT/API key auth layer | Dev | 2h | P0 |
| 3.4 | Create KantorTeman dashboard module | Dev | 6h | P1 |
| 3.5 | Implement real-time updates (polling) | Dev | 3h | P1 |
| 3.6 | E2E testing: Full conversation flow | Testing | 4h | P0 |
| 3.7 | Load testing (simulate 20 concurrent chats) | Testing | 2h | P1 |
| 3.8 | Error recovery + retry logic | Dev | 2h | P1 |

**Deliverables:**
- ✅ REST API documented
- ✅ Dashboard module in KantorTeman
- ✅ E2E flow works (receive → process → reply/ escalate → resolve)

**Definition of Done:**
- Full E2E test passes
- Dashboard shows real-time conversations
- Admin can takeover from KantorTeman dashboard

---

## SPRINT 4: POLISH + LAUNCH (Day 16-20)

### Goal: Bug fixes + Documentation + Beta release

**Tasks:**

| # | Task | Type | Est. Time | Priority |
|---|------|------|-----------|----------|
| 4.1 | Bug fixes from testing | Dev | 4h | P0 |
| 4.2 | Add rate limiting (prevent spam) | Dev | 2h | P0 |
| 4.3 | Implement backup automation | Dev | 2h | P1 |
| 4.4 | Setup monitoring + alerting (cron + Telegram) | Infra | 3h | P1 |
| 4.5 | Write user documentation (admin guide) | Docs | 2h | P1 |
| 4.6 | Write API documentation | Docs | 2h | P2 |
| 4.7 | Beta release with 3 pilot UMKM clients | Launch | 4h | P0 |
| 4.8 | Collect feedback + iterate | Review | 2h | P0 |

**Deliverables:**
- ✅ Production-ready bot
- ✅ Monitoring active
- ✅ 3 pilot clients onboarded

**Definition of Done:**
- Bot runs 24/7 without issues
- Monitoring alerts work
- Pilot clients using the bot

---

## MVP CHECKLIST

```
✅ Receive WhatsApp messages (Fontee API)
✅ Keyword matching (harga, promo, cara order, greeting)
✅ Auto-reply with templates
✅ Manual takeover flow
✅ Admin notification (Telegram)
✅ Dashboard view (conversations)
✅ Admin reply from dashboard
✅ Conversation logging (database)
✅ Basic metrics (auto-reply rate, response time)
✅ Error handling + recovery
```

---

## TASK BREAKDOWN (for Claude Code)

### Week 1 - Foundation
```markdown
## Setup Tasks
1. Create LXC container config
2. Install Node.js 20, PostgreSQL 16
3. Setup PM2 with auto-restart
4. Install Fontee API client
5. Create database schema
6. Build basic webhook handler
7. Test send/receive flow
```

### Week 2 - Core
```markdown
## Core Tasks
1. Keyword engine with priority matching
2. Auto-reply templates (greeting, keyword responses)
3. Confidence scoring algorithm
4. Escalation trigger + notification
5. Context transfer (last N messages)
6. Simple admin dashboard (HTML + JS)
7. Telegram webhook for admin alerts
```

### Week 3 - Integration
```markdown
## Integration Tasks
1. REST API (GET/POST conversations, POST reply)
2. JWT/API key authentication
3. KantorTeman dashboard module
4. Real-time polling
5. Full E2E test scenarios
6. Load test with 20 concurrent users
7. Error boundary + retry logic
```

### Week 4 - Polish
```markdown
## Polish Tasks
1. Rate limiter (requests per minute)
2. Backup script (daily)
3. Monitoring cron (health check every 5 min)
4. Alerting to Telegram
5. Admin documentation
6. Beta onboarding script
7. Feedback collection form
```

---

## TIMELINE SUMMARY

```
Day 1-2:  Infrastructure setup (VPS, Node, PostgreSQL, PM2)
Day 3-4:  Basic bot + Fontee integration
Day 5:    Database schema + basic receive/send

Day 6-7:  Keyword engine + templates
Day 8-9:  Escalation flow + admin notification
Day 10:   Simple dashboard

Day 11-12: REST API + auth
Day 13-14: KantorTeman dashboard module
Day 15:   E2E testing

Day 16-17: Bug fixes + rate limiting
Day 18:    Monitoring + backup
Day 19-20: Documentation + Beta launch
```

**Total: ~20 working days (4 weeks)**

---

## RESOURCE REQUIREMENTS

**VPS:**
- 2 vCPU
- 2GB RAM
- 10GB storage
- Ubuntu 22.04

**Tools:**
- Claude Code (VPS) - main coding
- PM2 - process manager
- PostgreSQL 16 - database
- Node.js 20 - runtime

---

*Document by Friday (IT PM)*