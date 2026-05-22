# Technical Reference — Kantor Teman CRM

## Stack

| Layer | Teknologi |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI (Python), SQLAlchemy ORM, SQLite |
| Auth | JWT (HS256), bcrypt password hashing |
| Deployment | LiteSpeed WSGI via `passenger_wsgi.py`, static Next.js build |
| AI | Anthropic Claude (via AIMurah proxy), Semuts.sh API (OpenAI-compatible) |

---

## Struktur Direktori

```
gmaps-lead-gen/
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
| `blast_campaigns` | Kampanye WhatsApp blast |
| `chat_projects` / `chat_conversations` | AI Chat dengan memory |
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
- Provider: Semuts.sh (OpenAI-compatible), model selector
- Export chat, markdown rendering

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

- `main` — stable
- `ai` — branch aktif (AI Chat + Project Board features)
