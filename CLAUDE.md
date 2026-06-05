# Kantor Teman — CRM untuk Agensi Digital

## What This Is
CRM internal untuk agensi digital kecil-menengah. Lead scraping → pipeline → proposal → project board → WhatsApp blast → AI chat — all in one.

## Stack
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend:** FastAPI (Python), SQLAlchemy ORM, MySQL (production) / SQLite (dev)
- **Auth:** JWT (HS256), bcrypt
- **Deploy:** LiteSpeed WSGI (shared hosting), Vercel (frontend)
- **AI:** 9router proxy (OpenAI-compatible → Claude, GPT-5, DeepSeek, MiMo)

## Project Structure
```
kantorteman/
├── backend/
│   ├── main.py                    (FastAPI entry — 206L)
│   ├── models/__init__.py        (53 SQLAlchemy models)
│   ├── schemas/__init__.py        (116 Pydantic schemas)
│   ├── routers/                  (13 route modules)
│   ├── app/core/                 (config, security, dependencies)
│   ├── app/services/             (business logic)
│   ├── app/schedulers/           (outreach cron)
│   ├── tests/                    (4 test files, all pass)
│   └── add_performance_indexes.sql
├── frontend/
│   ├── src/app/                  (Next.js pages — extracted)
│   ├── src/components/           (shared + extracted components)
│   └── src/lib/                  (utilities, api client)
├── hermes-gateway/               (independent AI agent middleware)
├── CLAUDE.md                     (this file)
├── OVERVIEW.md                   (product overview)
├── TECHNICAL.md                  (tech reference)
└── PRODUCTION.md                (deployment guide)
```

## Database
**Production: MySQL** | **Development: SQLite**

Tables: `users`, `leads`, `contacts`, `projects`, `proposals`, `boards`, `board_columns`, `board_cards`, `board_card_comments`, `board_card_checklists`, `board_card_activities`, `client_notes`, `client_credentials`, `blast_campaigns`, `blast_messages`, `follow_up_sequences`, `reengagement_alerts`, `chat_projects`, `chat_conversations`, `content_sessions`, `content_generations`, `workspaces`, `workspace_sheets`, `client_documents`, `document_templates`, `ai_proxies`, `provider_configs`, `audit_logs`

## Key Router Modules
`analytics.py`, `auth.py`, `campaign.py`, `clients.py`, `content.py`, `documents.py`, `finance.py`, `leads.py`, `office.py`, `other.py`, `proposals.py`, `settings.py`, `workspace.py`

## Deployment
```bash
# Backend (LiteSpeed WSGI)
python migrate.py && touch tmp/restart.txt

# Frontend (Vercel)
cd frontend && npm run build && git push
```

## Auth Flow
Login → `POST /api/login` → JWT 24h in cookie `kt_token`. User name in localStorage `kt_name`. All endpoints need `Depends(get_current_user)`.

## AI Routing (9router)
Default: `http://localhost:20128/v1`. Combos: `combo-kiro` (Claude), `combo-mimo` (MiMo), `combo-deepseek` (DeepSeek), `combo-freemodel` (GPT-5).

## Current Branch
`main` — production ready.

## Completed Optimizations (2026-06-05)

### Backend
- ✅ Modularization: main.py 11,471L → 206L (models/schemas/routers split)
- ✅ Security: Gemini key in header (not URL), Jinja2 SandboxedEnvironment, rate limits on wa/send, followup/*
- ✅ N+1 query fixes in finance, clients, workspace endpoints
- ✅ Performance indexes added
- ✅ 4 test suites: security (14), finance (7), campaign (6), hardening (11) — all PASS

### Frontend
- ✅ Mega-files split: documents (1380L → 162L), 6 pages extracted
- ✅ Shared code consolidated: formatRupiah, inputCls, download utils
- ✅ Loading/Error boundaries added
- ✅ Security headers: CSP, X-Frame-Options, etc.
- ✅ Dead code removed: 6 unused hooks, SuspenseWrapper

## Known Issues
None — all critical issues resolved.

## Running Commands
```bash
# Backend tests
cd backend && source venv/bin/activate && python -m pytest tests/ -v

# Frontend typecheck
cd frontend && npx tsc --noEmit

# Dev server
cd backend && uvicorn main:app --reload --port 8000 &
cd frontend && npm run dev
```