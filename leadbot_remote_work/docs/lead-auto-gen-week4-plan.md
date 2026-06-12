# WEEK 4 EXECUTION PLAN - Lead Auto Gen
**Start:** 7 Juni 2026 14:22 WIB
**Target:** Production-ready MVP
**Timeline:** 2-3 days

---

## DAY 1: STABILITY & SECURITY

### Morning (09:00-12:00)
**4.1 Bug Fixes & Testing**
```bash
# Test scenarios to run:
1. Keyword matching (all 5 keywords)
2. No-match fallback
3. Conversation escalation
4. Dashboard CRUD operations
5. Edge cases:
   - Empty message
   - Special characters (@#$%)
   - Very long message (>1000 chars)
   - Rapid-fire messages (spam test)
   - Multiple simultaneous conversations
```

**4.2 Rate Limiting**
```javascript
// Implementation targets:
- Per-phone: 10 messages/minute
- Global: 100 messages/minute
- Return HTTP 429 on violation
- Log violations to DB
```

### Afternoon (13:00-17:00)
**4.3 Backup Automation**
```bash
# Setup cron job:
0 3 * * * /opt/leadbot/scripts/backup.sh

# Backup script requirements:
- Dump PostgreSQL database
- Compress (gzip)
- Store in /opt/leadbot/backups/
- Keep last 7 days
- Alert on failure (Telegram)
```

**4.4 Monitoring Setup (Part 1)**
```bash
# Health check cron:
*/5 * * * * /opt/leadbot/scripts/healthcheck.sh

# Check:
- API responsive (curl localhost:3000/api/health)
- DB connection alive
- PM2 process running
- Disk usage <85%
```

---

## DAY 2: DOCUMENTATION & POLISH

### Morning (09:00-12:00)
**4.5 User Documentation**
```markdown
# Create docs:
1. README.md - Project overview
2. SETUP.md - Installation guide
3. ADMIN_GUIDE.md - Dashboard usage
4. TROUBLESHOOTING.md - Common issues
```

**4.6 API Documentation**
```markdown
# Document endpoints:
- GET /api/health
- GET /api/dashboard/stats
- GET /api/dashboard/conversations
- GET /api/dashboard/keywords
- POST /api/dashboard/keywords
- DELETE /api/dashboard/keywords/:id
- POST /api/dashboard/reply
- POST /api/webhook (Fontee)
```

### Afternoon (13:00-17:00)
**4.4 Monitoring Setup (Part 2)**
```bash
# Alert system:
- Telegram notification on:
  * API down >2 minutes
  * DB connection failure
  * Disk usage >85%
  * Backup failure
  * Rate limit violations (summary hourly)
```

**4.7 Beta Release Checklist**
```markdown
## Pre-launch Checklist:
- [ ] All endpoints tested
- [ ] Rate limiting active
- [ ] Backup cron running
- [ ] Monitoring active
- [ ] Documentation complete
- [ ] Security audit done
- [ ] Performance baseline recorded
- [ ] Rollback plan documented
```

---

## DAY 3: BETA LAUNCH

### Morning (09:00-12:00)
**Security Audit**
```bash
# Check:
1. Environment variables secured (.env not exposed)
2. API endpoints require auth (if needed)
3. SQL injection prevention (parameterized queries)
4. XSS prevention (sanitize inputs)
5. Rate limiting active
6. Error messages don't leak sensitive info
```

**Performance Test**
```bash
# Baseline metrics:
- Response time: <200ms (p95)
- Throughput: 50 concurrent users
- Database queries: <50ms
- Memory stable: <100MB
```

### Afternoon (13:00-17:00)
**Launch & Monitor**
```bash
# Launch steps:
1. Final smoke test
2. Enable monitoring alerts
3. Announce to beta users
4. Monitor first 2 hours closely
5. Document any issues
```

**4.8 Feedback Collection**
```markdown
# Setup:
- Feedback form (Google Form / Typeform)
- Bug report template (GitHub Issues)
- Feature request process
- Support channel (Telegram group?)
```

---

## TASK ASSIGNMENTS (Claude Code)

### Batch 1: Stability (Day 1 Morning)
```markdown
1. Write comprehensive test suite
2. Implement rate limiting middleware
3. Add edge case handling
4. Fix any bugs discovered
```

### Batch 2: Automation (Day 1 Afternoon)
```markdown
1. Create backup.sh script
2. Create healthcheck.sh script
3. Setup cron jobs
4. Test backup/restore flow
```

### Batch 3: Documentation (Day 2 Morning)
```markdown
1. Write README.md
2. Write SETUP.md
3. Write ADMIN_GUIDE.md
4. Write API_DOCS.md
```

### Batch 4: Monitoring (Day 2 Afternoon)
```markdown
1. Implement Telegram alerting
2. Create monitoring dashboard (optional)
3. Test all alert scenarios
4. Document alert thresholds
```

### Batch 5: Launch Prep (Day 3)
```markdown
1. Security audit
2. Performance baseline
3. Final smoke test
4. Launch checklist execution
```

---

## SUCCESS CRITERIA

**MVP Launch = ✅ when:**
- [ ] Bot auto-replies to keywords correctly
- [ ] Dashboard shows conversations & stats
- [ ] Admin can reply from dashboard
- [ ] Rate limiting prevents spam
- [ ] Backups running daily
- [ ] Monitoring alerts active
- [ ] Documentation complete
- [ ] 3 beta users onboarded

---

## ROLLBACK PLAN

**If critical bug discovered:**
1. Stop PM2 process: `pm2 stop leadbot`
2. Restore last backup: `/opt/leadbot/scripts/restore.sh [backup-file]`
3. Investigate issue offline
4. Fix & redeploy
5. Resume: `pm2 restart leadbot`

---

*Execution by Friday via Claude Code*