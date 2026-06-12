# LeadBot - Panduan Penggunaan

## Overview

LeadBot adalah WhatsApp bot untuk auto-reply dan lead management.

**Access:**
- Dashboard: http://202.6.204.179:20035/
- Telegram: @TemanCiaBot

## Dashboard

### Conversations Tab
- Klik icon chat (biru) untuk buka conversation
- Klik icon escalate (orange) untuk eskalasi
- Klik icon close (abu) untuk tutup conversation

### Keywords Tab
- Klik + (hijau) untuk tambah keyword
- Klik edit (biru) untuk ubah keyword
- Klik hapus (merah) untuk hapus keyword

## Telegram Commands

- /start - Welcome
- /stats - View stats
- /conversations - List chats
- /reply phone message - Send WA reply
- /broadcast message - Send to all
- /test - Test bot

## API Endpoints

- GET /api/health - Health check
- POST /api/webhook - Fonnte webhook
- GET /api/dashboard/stats - Stats
- GET /api/dashboard/conversations - List chats
- POST /api/dashboard/keywords - Add keyword

## Troubleshooting

pm2 logs leadbot - View logs
pm2 restart leadbot - Restart bot
pm2 status - Check status

## Database

sudo -u postgres psql -d leadbot_db

Queries:
- SELECT * FROM conversations;
- SELECT * FROM messages;
- SELECT * FROM keywords;
