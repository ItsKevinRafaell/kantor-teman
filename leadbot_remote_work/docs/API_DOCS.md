# LeadBot API Documentation

## Base URL


## Authentication
No auth required for dashboard endpoints (internal use).
Rate limiting: 100 requests/minute global.

---

## Endpoints

### Health

#### GET /health
Health check with rate limit stats.

**Response:**
{"status":"ok","timestamp":"2026-06-08T03:00:00.000Z","rateLimit":{"activePhones":0,"totalRequests":0,"globalCount":0}}

---

### Dashboard - Stats

#### GET /dashboard/stats
Dashboard statistics (cached 30 seconds).

**Response:**
{"total":10,"active":5,"escalated":2,"messagesToday":45,"autoRepliedToday":38,"escalatedToday":3,"autoReplyRate":84}

---

### Dashboard - Conversations

#### GET /dashboard/conversations
List active and escalated conversations.

#### GET /dashboard/conversations/:id
Get messages for a conversation.

#### POST /dashboard/conversations/:id/reply
Send WhatsApp reply.
Body: {"message": "text"}

#### POST /dashboard/conversations/:id/escalate
Mark as escalated.
Body: {"reason": "text"}

#### POST /dashboard/conversations/:id/close
Close conversation.

---

### Dashboard - Leads

#### GET /dashboard/leads
Get lead candidates (escalated conversations).

---

### Dashboard - Keywords

#### GET /dashboard/keywords
List all keywords.

#### POST /dashboard/keywords
Add keyword.
Body: {"keyword":"text","response":"text","priority":0}

#### PUT /dashboard/keywords/:id
Update keyword.

#### DELETE /dashboard/keywords/:id
Delete keyword.

---

### Webhook (Fonnte)

#### POST /webhook
Fonnte WhatsApp webhook.
Body: {"sender":"628123456789","message":"text","name":"Name"}
Response: {"success":true,"autoReply":true,"leadCandidate":true,"leadCreated":true,"leadId":123}

---

## Rate Limits
Per Phone: 10 requests/minute
Global: 100 requests/minute
Returns HTTP 429 when exceeded.

---

## Error Responses
400: Invalid payload
404: Resource not found
429: Rate limit exceeded
500: Server error
