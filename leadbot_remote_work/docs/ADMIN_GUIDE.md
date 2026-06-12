# LeadBot Admin Guide

## Dashboard
Access: http://202.6.204.179:20035/

### Conversations Tab
- View all active & escalated conversations
- Click chat icon to open conversation
- Click escalate icon (orange) to mark as lead
- Click close icon to close conversation
- Click reply to send manual response

### Keywords Tab
- Auto-reply keyword management
- Click + to add new keyword
- Click edit to modify
- Click delete to remove
- Priority: higher = checked first

### Lead Candidates
- GET /api/dashboard/leads
- Shows escalated conversations for lead review

## API Endpoints

### Health & Status
GET /api/health
- Returns: {status, timestamp, rateLimit}

GET /api/dashboard/stats
- Returns: {total, active, escalated, messagesToday, autoRepliedToday, escalatedToday, autoReplyRate}

### Conversations
GET /api/dashboard/conversations
- Returns: List of active/escalated conversations

GET /api/dashboard/conversations/:id
- Returns: Messages for conversation

POST /api/dashboard/conversations/:id/reply
- Body: {message: string}
- Sends WhatsApp reply

POST /api/dashboard/conversations/:id/escalate
- Body: {reason: string}
- Marks as escalated

POST /api/dashboard/conversations/:id/close
- Marks conversation as closed

### Leads
GET /api/dashboard/leads
- Returns: Lead candidates (escalated conversations)

### Keywords
GET /api/dashboard/keywords
POST /api/dashboard/keywords - Body: {keyword, response, priority}
PUT /api/dashboard/keywords/:id - Body: {keyword, response, priority}
DELETE /api/dashboard/keywords/:id

### Webhook
POST /api/webhook
- Fonnte webhook endpoint (not for manual use)

## Rate Limiting
- Per phone: 10 messages/minute
- Global: 100 messages/minute
- Returns 429 when exceeded

## Cron Jobs
- Backup: Daily 3:00 AM
- Healthcheck: Every 5 minutes

## Commands
pm2 restart leadbot
pm2 logs leadbot --lines 50
