# BACKLOG - Lead Auto Gen
**Last Updated:** 7 Juni 2026 14:21 WIB

## STATUS LEGEND
- [ ] = Todo
- [P] = In Progress
- [D] = Done
- [B] = Blocked

---

## SPRINT 1: FOUNDATION ✅ DONE

| Status | Task | Assignee | Notes |
|--------|------|----------|-------|
| [D] | 1.1 Provision VPS LXC container | Friday | Node.js 20 + PostgreSQL 14 ✅ |
| [D] | 1.2 Setup PM2 process manager | Friday | Auto-restart enabled ✅ |
| [D] | 1.3 Install Fontee API SDK | Friday | Configured ✅ |
| [D] | 1.4 Build basic message handler | Friday | Receive + echo test ✅ |
| [D] | 1.5 Setup webhook listener | Friday | Incoming messages ✅ |
| [D] | 1.6 Database schema | Friday | conversations, messages, keywords ✅ |
| [D] | 1.7 Test send/receive | Friday | E2E verify ✅ |

---

## SPRINT 2: CORE FEATURES ✅ DONE

| Status | Task | Assignee | Notes |
|--------|------|----------|-------|
| [D] | 2.1 Keyword matching engine | Friday | Priority-based ✅ |
| [D] | 2.2 Auto-reply templates | Friday | 5 keywords configured ✅ |
| [D] | 2.3 Confidence scoring | Friday | <70% → escalate ✅ |
| [D] | 2.4 Admin notification | Friday | Telegram service ready ✅ |
| [D] | 2.5 Conversation history view | Friday | Dashboard UI complete ✅ |
| [D] | 2.6 Admin reply interface | Friday | Send via dashboard ✅ |
| [D] | 2.7 Handoff context transfer | Friday | Last 10 messages ✅ |
| [D] | 2.8 Basic metrics | Friday | Stats API working ✅ |

**Deliverables:**
- ✅ 2 test conversations logged
- ✅ Keywords: halo, hallo, info, harga, produk
- ✅ Dashboard: http://202.6.204.179:3000/

---

## SPRINT 3: INTEGRATION (SKIPPED)

**Decision:** KantorTeman integration deferred to post-MVP.

---

## SPRINT 4: POLISH + LAUNCH 🔄 IN PROGRESS

| Status | Task | Assignee | Priority | Notes |
|--------|------|----------|----------|-------|
| [ ] | 4.1 Bug fixes | Friday | P0 | From testing |
| [ ] | 4.2 Rate limiting | Friday | P0 | Anti-spam |
| [ ] | 4.3 Backup automation | Friday | P1 | Daily DB backup |
| [ ] | 4.4 Monitoring + alerting | Friday | P1 | Cron + Telegram |
| [ ] | 4.5 User documentation | Friday | P1 | Admin guide |
| [ ] | 4.6 API documentation | Friday | P2 | Endpoints list |
| [ ] | 4.7 Beta release prep | Friday | P0 | Production checklist |
| [ ] | 4.8 Feedback collection | Friday | P0 | Post-launch |

---

## CURRENT SPRINT DETAILS

### Week 4 Tasks

#### 4.1 Bug Fixes (P0)
- Test all keyword combinations
- Test conversation escalation
- Verify dashboard CRUD
- Edge cases (empty message, special chars, etc.)

#### 4.2 Rate Limiting (P0)
- Implement per-phone rate limit (10 msg/min)
- Global rate limit (100 msg/min)
- Return 429 on rate limit hit
- Log rate limit violations

#### 4.3 Backup Automation (P1)
- Daily PostgreSQL backup (3am WIB)
- Retention: 7 days
- Backup location: `/opt/leadbot/backups/`
- Alert on backup failure

#### 4.4 Monitoring + Alerting (P1)
- Health check cron (every 5 min)
- Alert if API down (Telegram)
- Alert if DB connection fails
- Alert if disk >85%

#### 4.5 User Documentation (P1)
- Setup guide
- Keyword management guide
- Conversation handling guide
- Troubleshooting

#### 4.6 API Documentation (P2)
- Endpoint list
- Request/response examples
- Authentication
- Error codes

#### 4.7 Beta Release Prep (P0)
- Production checklist
- Security audit
- Performance test
- Rollback plan

#### 4.8 Feedback Collection (P0)
- Beta user feedback form
- Bug report template
- Feature request process

---

## BLOCKERS (RESOLVED)

| # | Blocker | Status | Resolution |
|---|---------|--------|------------|
| ~~1~~ | ~~Fontee API credentials~~ | ✅ Resolved | Configured |
| ~~2~~ | ~~VPS SSH access~~ | ✅ Resolved | Access granted |
| 3 | Telegram bot token | 🟡 Optional | Not blocking Week 4 |

---

## DECISIONS LOG

| Date | Decision | Rationale |
|------|----------|-----------|
| 7 Jun 2026 | Self-hosted + Fontee API | Control + cost efficient |
| 7 Jun 2026 | PostgreSQL for logs | Reliable, structured queries |
| 7 Jun 2026 | PM2 for process mgmt | Auto-restart, monitoring |
| 7 Jun 2026 | Vanilla HTML dashboard | Resource efficient (36MB RAM vs 500MB Next.js) |
| 7 Jun 2026 | Skip KantorTeman integration (Sprint 3) | Focus on MVP stability |
| 7 Jun 2026 | Stick with vanilla stack | VPS constraints: 75% disk, no swap |

---

## RESOURCE STATUS

**VPS Health:**
- RAM: 3.4GB / 4GB free
- Disk: 1.9GB / 7.8GB free (75% used)
- CPU: 2 cores
- Swap: 0 (no buffer)

**Current Services:**
- LeadBot API: ~36MB RAM (PID 124952)
- PostgreSQL 14: Active
- PM2: Running

---

*Managed by Friday (IT PM)*