# feat/backend-caching — Task List

> Branch: `feat/backend-caching` | Worktree: `/home/kevin/kantorteman/.worktrees/backend`
> Target: Fase 2 backend optimization — service layer + caching
> Deadline: secepatnya, yang penting benar

---

## ⚠️ Critical Rules

- **Passenger WSGI**: Semua async harus pakai `threading.Thread` — jangan pernah ganti
- **SQLite**: pakai `NullPool` — jangan diubah
- **Foreign keys**: `PRAGMA foreign_keys = ON` per koneksi — jangan dihapus
- **Endpoint signature**: semua path harus tetap persis sama — frontend bergantung ke API ini
- **Auth**: JWT + bcrypt + `Depends(get_current_user)` — jangan disentuh
- **Commit**: 1 task = 1 commit

---

## Task 1: Service Layer — Finance

**File baru**: `backend/app/services/finance_service.py`

Extract dari `routers/finance.py`:
- `calculate_financial_summary()` — agregasi wallet, runway, break-even
- `calculate_expense_by_category()` — group by category
- `get_wallet_balance()` — query + cache 60 detik
- `create_transaction()` — validasi + insert + update saldo

**Verifikasi**: `python backend/tests/test_api_contracts.py` finance endpoint tetap pass
**Commit**: `feat(backend): add finance service layer`

---

## Task 2: Service Layer — Leads

**File baru**: `backend/app/services/lead_service.py`

- `search_leads()` — query + filter + sort + paginate
- `update_lead_status()` — validasi state transition + audit log
- `calculate_lead_score()` — scoring logic terpisah dari endpoint
- `export_leads_csv()` — CSV generation

**Verifikasi**: contract test leads endpoint
**Commit**: `feat(backend): add lead service layer`

---

## Task 3: Service Layer — Workspace

**File baru**: `backend/app/services/workspace_service.py`

- `init_workspace_sheets()` — auto-generate template sheets
- `get_workspace_summary()` — aggregate rows/columns/cells
- `update_cell()` — update + recalc

**Verifikasi**: contract test workspace
**Commit**: `feat(backend): add workspace service layer`

---

## Task 4: Caching Layer

**File baru**: `backend/app/core/cache.py`

- In-memory TTL cache (`dict` + `time.time()`)
- Decorator `@cached(ttl_seconds=60)`
- Apply ke: `GET /api/finance/transactions`, `GET /api/workspace-list`
- Invalidate cache pas write (POST/PUT/DELETE)

**Verifikasi**: hit endpoint 2x → response time kedua jauh lebih cepat
**Commit**: `feat(backend): add TTL cache for polling endpoints`

---

## Task 5: Wire & Verify

- Update `routers/finance.py`, `routers/leads.py`, `routers/workspace.py` — ganti inline logic ke service call
- Router endpoint signature tetap — ganti isi aja
- Full test: `python -m pytest backend/tests/ -v`
- Kalau fail → fix dulu, jangan skip
- Kalau pass → merge ke `main`

**Commit**: `feat(backend): wire service layer to routers`
