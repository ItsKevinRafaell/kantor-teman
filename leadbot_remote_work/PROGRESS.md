# LeadBot Project Progress
## Last Updated: 2026-06-08

## Access
- Dashboard: http://202.6.204.179:20035/
- API: http://202.6.204.179:20035/api
- Telegram: @TemanCiaBot

## Week 3-4 COMPLETED

### Foundation (Day 1-2)
- [x] Keyword caching (node-cache, 5min TTL)
- [x] Regex scoring (exact=100, partial=50, regex=30)
- [x] Intent detection (7 categories)
- [x] Lead trigger detection
- [x] Stats cache (30s TTL) with autoReplyRate
- [x] Source column in conversations

### Lead Auto-Gen (Day 3)
- [x] leadService.js with KantorTeman API
- [x] Phone extraction & normalization
- [x] Product interest categorization
- [x] Lead dedup cache (1 hour)

### Integration (Day 4)
- [x] Rate limiter (10/min phone, 100/min global)
- [x] KantorTeman API key generated
- [x] backup.sh + healthcheck.sh
- [x] Cron jobs active

### Documentation (Day 5-6)
- [x] ADMIN_GUIDE.md
- [x] API_DOCS.md
- [x] E2E testing

## Pending
- [ ] Register API key in KantorTeman settings
- [ ] Dashboard auto-refresh (optional)
