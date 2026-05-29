# Kantor Teman — CRM Internal untuk Agensi Digital

CRM all-in-one untuk agensi digital skala kecil-menengah. Dari scraping leads → blast WhatsApp → proposal publik → project board kanban — semua dalam satu dashboard.

## Fitur Utama

- **Lead Generation** — scrape Google Maps by category + lokasi, auto-score 0–85
- **WhatsApp Blast** — Fonnte API integration, template dengan variabel personalisasi
- **Report Page Publik** — `/report/{slug}` dengan Pain Box, ROI Slider, FOMO Timer, lead scoring
- **Proposal Multi-Service** — link publik `/p/{slug}`, accept/reject flow, analytics waktu baca
- **Project Board** — kanban Trello-like dengan kolom, card, checklist, comments, drag & drop
- **Workspace Sheets** — spreadsheet per project dengan auto-init template per service type
- **Finance Tracker** — wallet, transaksi, subscription, auto-deduct
- **AI Chat** — multi-project, multi-conversation dengan memory bank
- **Brand Kit** — colors, fonts, logos, public API endpoint
- **Audit Log** — semua aksi CRUD ter-record

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, SQLite |
| Auth | JWT (HS256) + bcrypt |
| Deploy | LiteSpeed WSGI |
| AI | 9router (local OpenAI-compatible proxy → Claude, DeepSeek, MiMo, GPT-5) |
| WhatsApp | Fonnte API |

## Quick Start (Development)

### Backend

```bash
cd backend

# Setup env
cp .env.example .env
# Edit .env: GOOGLE_API_KEY, JWT_SECRET, SECRET_ENCRYPTION_KEY, FONNTE_TOKEN

# Virtualenv + deps
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# DB migration + seed
python migrate.py
python seed.py

# Run dev server
uvicorn main:app --reload --port 8000
```

Backend: http://localhost:8000  
API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend

cp .env.local.example .env.local
# Edit: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_ADMIN_WA

npm install
npm run dev
```

Frontend: http://localhost:3000

### Default Login

```
Email: admin@kantorteman.com
Password: admin123
```

> Ganti password segera setelah login pertama.

## Dokumentasi

- [OVERVIEW.md](./OVERVIEW.md) — gambaran produk untuk user
- [TECHNICAL.md](./TECHNICAL.md) — referensi teknis (models, endpoints, deployment)
- [PRODUCTION.md](./PRODUCTION.md) — production launch guide
- [MARKETING_FLOW.md](./MARKETING_FLOW.md) — end-to-end marketing automation flow
- [BACKLOG_REVIEW.md](./BACKLOG_REVIEW.md) — backlog progress

## Lisensi

Internal use — Kantor Teman.
