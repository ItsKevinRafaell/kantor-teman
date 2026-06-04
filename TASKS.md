# feat/backend-caching — Phase 2: Cleanup Routers

> Branch: `feat/backend-caching` | Worktree: backend

## ⚠️ Rules
- Jangan ubah endpoint signature
- Commit 1 task = 1 commit
- Service layer sudah ada — router tinggal panggil service

---

## Task 1: Bersihin import finance router
- `routers/finance.py` import 53 model + ~40 dependencies. Ganti import model jadi spesifik (cuma yang dipakai: Transaction, Wallet, Subscription, Lead, AuditLog).
- Dependencies yang nggak dipakai dihapus dari import

## Task 2: Bersihin import leads router  
- Sama — `routers/leads.py` import semua model tapi cuma pakai sebagian

## Task 3: Bersihin import workspace router
- Sama — `routers/workspace.py`

## Task 4: Bersihin import router sisanya (10 file)
- `routers/auth.py`, `routers/clients.py`, `routers/content.py`, `routers/campaign.py`, `routers/documents.py`, `routers/proposals.py`, `routers/settings.py`, `routers/analytics.py`, `routers/office.py`, `routers/other.py`

---

Kalau selesai → merge ke main.
