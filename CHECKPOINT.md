# Checkpoint — 2025-06-04

## Status Terakhir

### Commit HEAD
- `4f3c105` — `chore(merge): frontend types, auth, SWR, hooks, component extraction`

### State
- Branch: `main`
- Ada uncommitted change di `.commandcode/taste/workflow/taste.md` (modified)
- Worktrees ada untuk `backend` dan `frontend` (belum dipakai)

---

## Backend — Progress & Issues

### Progress Fase 1 ✅
Lihat: `backend/PROGRESS_FASE1.md`
- `app/core/config.py` — env extraction ✅
- `app/core/database.py` — DB setup terpisah ✅
- `app/core/security.py` — auth helpers ✅
- `scripts/init_db.py` — standalone DB init ✅
- `tests/test_api_contracts.py` — 55 endpoint contract test ✅

### Fase 2 (BELUM)
- Service layer & caching — belum dikerjakan

### Bug / Issue

#### 1. `routers/other.py:25` — `Lead` not imported
- **File:** `backend/routers/other.py` line 11
- **Masalah:** `send_wa_manual` di line 25 pakai `db.query(Lead)` tapi `Lead` ga ada di import
- **Fix:** tambahin `Lead` ke baris import:
  ```
  from models import get_db, log_audit, Lead, User, MessageTemplate, ...
  ```
- **Test yang fail:** `test_hardening.py::test_opt_out_blocks_manual_whatsapp_before_provider_call`

#### 2. `test_api_contracts.py` — butuh server jalan
- **60 test fail** karena backend ga running di `localhost:8000`
- **Cara run:**
  ```bash
  cd backend && source venv/bin/activate
  uvicorn main:app --host 0.0.0.0 --port 8000 &
  API_URL=http://localhost:8000 python -m pytest tests/test_api_contracts.py -v
  ```
- 10 hardening unit test pass tanpa server karena pakai `import main` langsung

### Cara Masuk Project
```bash
# Backend
cd backend && source venv/bin/activate
python -m pytest tests/test_hardening.py -v   # unit test (no server needed)
uvicorn main:app --reload --port 8000          # jalankan server

# Frontend
cd frontend && npm run dev                     # Next.js dev server di :3000
```

---

## Frontend — Progress

### Yang sudah dikerjakan (dari commit history)
- TypeScript types consolidation
- Auth flow dengan SWR
- Custom hooks: `useLeads`, `useDashboard`
- Component extraction: `client-detail` dipecah dari monolith 1159L
- Unused imports cleanup di routers, workspace, leads, finance

### Stack
- Next.js 14.2.5 (App Router), React 18, TypeScript, Tailwind, SWR, Lucide, Leaflet
- Belum ada test framework / test file di frontend
