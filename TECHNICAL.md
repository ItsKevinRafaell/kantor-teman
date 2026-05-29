# Technical Reference — Kantor Teman CRM

## Stack

| Layer | Teknologi |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI (Python), SQLAlchemy ORM, SQLite |
| Auth | JWT (HS256), bcrypt password hashing |
| Deployment | LiteSpeed WSGI via `passenger_wsgi.py`, static Next.js build |
| AI | 9router (local OpenAI-compatible proxy → Claude Sonnet 4.6/4.7, DeepSeek v4, MiMo v2.5, GPT-5) |

---

## Struktur Direktori

```
kantorteman/
├── backend/
│   ├── main.py          # FastAPI app, semua model & endpoint
│   ├── migrate.py       # Migration script SQLite (idempotent)
│   └── leads.db         # SQLite database
└── frontend/
    ├── src/app/         # Next.js pages (App Router)
    ├── src/components/  # Shared components (Sidebar, Toast, dll)
    └── src/lib/api.ts   # apiFetch wrapper + auth token
```

---

## Database Models

| Tabel | Deskripsi |
|---|---|
| `users` | Akun login (id, name, email, hashed_password) |
| `leads` | Data bisnis hasil scraping Google Maps |
| `contacts` | Klien aktif yang sudah dikualifikasi |
| `projects` | Proyek per klien (FIXED/RETAINER, is_archived, color) |
| `proposals` | Proposal multi-service dengan analytics view |
| `boards` | Board kanban per proyek |
| `board_columns` | Kolom board (To Do, In Progress, dll) dengan color |
| `board_cards` | Card tugas (assignee, due_date, labels, color, lead_id) |
| `board_card_comments` | Komentar per card |
| `board_card_checklists` | Checklist item per card |
| `board_card_activities` | Activity log per card |
| `client_notes` | Catatan interaksi per klien |
| `client_credentials` | Kredensial akses klien (terenkripsi Fernet) |
| `blast_campaigns` / `blast_messages` | Kampanye & pesan WhatsApp blast |
| `follow_up_sequences` | Sequence followup per lead (template + delay) |
| `reengagement_alerts` | Alert re-engagement otomatis |
| `chat_projects` / `chat_conversations` | AI Chat dengan memory |
| `content_sessions` / `content_generations` | Content generator sessions & hasil |
| `workspaces` / `workspace_sheets` | Spreadsheet per project |
| `client_documents` / `document_templates` | Dokumen & template HTML |
| `ai_proxies` | Konfigurasi proxy AI (9router) |
| `provider_configs` | Konfigurasi provider & quota (Fonnte, Claude, dll) |
| `audit_logs` | Log semua aksi CRUD user |

---

## API Endpoints (Board)

```
GET    /api/boards/overview?show_archived=bool
GET    /api/projects/{id}/board
POST   /api/boards/{id}/columns
PUT    /api/board-columns/{id}
DELETE /api/board-columns/{id}
POST   /api/board-columns/{id}/cards
GET    /api/board-cards/{id}
PUT    /api/board-cards/{id}
DELETE /api/board-cards/{id}
POST   /api/board-cards/{id}/move
POST   /api/board-cards/{id}/comments
POST   /api/board-cards/{id}/checklist
PATCH  /api/board-cards/{id}/checklist/{item_id}?is_done=bool
PATCH  /api/projects/{id}/color
PATCH  /api/projects/{id}/archive
```

---

## Fitur Utama per Modul

### CRM
- Scraping Google Maps → leads dengan koordinat, rating, website
- Pipeline: Leads → Contacts → Projects → Board
- Proposal multi-service dengan link publik, analytics (waktu baca, sections viewed)

### Project Board (Trello-like)
- CRUD project, kolom, card
- Drag & drop kartu antar kolom
- Color picker per proyek, kolom, dan card
- Assignee auto-fill dari session login
- Client assignment per card (atau inherit dari proyek)
- Checklist dengan progress bar + activity log realtime
- Archive card & project, filter arsip

### AI Chat
- Multi-project, multi-conversation dengan memory bank
- Provider: 9router (OpenAI-compatible), model selector per conversation
- Export chat, markdown rendering

### Content Generator
- Generate IG Carousel, IG Reels, SEO Article, TikTok, YouTube via AI
- Provider: 9router combo (configurable per feature via feature-defaults)
- Schedule content, track generation history

### Followup & Outreach Lifecycle
- Followup sequences per lead: configurable template + delay intervals
- Outreach lifecycle state machine (jalan tiap 1 jam): auto-escalate BLASTED → FOLLOWUP_QUEUE, REPORT_VIEWED → WARM_STAGNANT
- Enable via Settings: `followup_enabled=true`, `followup_hour=<jam WIB>`

### Workspace Sheets
- Spreadsheet per project, auto-init template per service type
- CRUD: init, sheets, rows, columns, cells

### Documents
- Generate dokumen dari template HTML (invoice, dll)
- Download, email ke klien

### WhatsApp Blast
- Integrasi Fonnte API
- Background task via threading (WSGI-safe, tanpa asyncio)
- Campaign tracking (cost, conversion)

---

## Deployment

```bash
# Backend
python migrate.py        # jalankan sebelum restart
touch tmp/restart.txt    # restart LiteSpeed passenger

# Frontend (upload .next/ dari build)
npm run build
# zip: .next/, public/, package.json, next.config.js
```

### Constraints LiteSpeed
- Maksimal 6 LSAPI workers
- Tidak boleh `asyncio.ensure_future()` — gunakan `threading.Thread`
- Database: SQLite dengan `NullPool` (no connection pooling)
- Foreign keys: `PRAGMA foreign_keys = ON` per koneksi

---

## Auth Flow

1. Login → `POST /api/login` → JWT token (24 jam)
2. Token disimpan di cookie `kt_token`
3. Nama user di `localStorage.kt_name`, email di `kt_email`
4. Semua endpoint protected via `Depends(get_current_user)`

---

## Branch

- `main` — stable + active development

---

## AI Routing (9router)

Semua panggilan AI dirutekan via 9router (proxy lokal OpenAI-compatible). Default `base_url`: `http://localhost:20128/v1` (override via env `NINE_ROUTER_URL` atau setting `ai_proxy_url`).

### Combos
| Combo | Model |
|---|---|
| `combo-kiro` | Claude Sonnet 4.6/4.7 |
| `combo-mimo` | MiMo v2.5 Pro (Xiaomi) |
| `combo-deepseek` | DeepSeek v4 Pro |
| `combo-freemodel` | GPT-5 (free) |
| `combo-test-mimo` | MiMo Test |

### Per-feature override
`ai_feature_defaults` (JSON di SystemSettings): map `feature → combo`. Fitur valid: `chat`, `article`, `image`, `analysis`, `caption`. Fallback ke active combo jika kosong.

### Endpoint
- `GET /api/ai/proxy-url` / `POST /api/ai/proxy-url` — set proxy URL
- `GET /api/ai/feature-defaults` / `POST /api/ai/feature-defaults` — per-feature combo override
- `GET /api/ai/health` — cek konektivitas proxy
