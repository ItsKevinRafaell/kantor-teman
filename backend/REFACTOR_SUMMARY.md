# Backend Refactor & Performance Optimization Summary

## Sebelum (Before)

| Masalah | Dampak |
|---------|--------|
| `main.py` 11,471 baris — semua models, schemas, dan 271 endpoint jadi satu file | Susah debug, susah maintain, rawan merge conflict |
| N+1 queries di 3 endpoint critical (transactions, client activity, workspace list) | 30+ database round-trip per halaman, load 5-10 detik |
| Index database kurang di beberapa kolom (leads deleted_at, board_cards is_archived, documents updated_at) | Full table scan, query lambat |
| `next.config.js` — `images.unoptimized: true` | Next.js image optimization mati, LCP jelek |

---

## Sesudah (After)

### 1. Struktur File — Modular

```
backend/
├── main.py                    (  206 baris)  ← app config, middleware, helpers
├── models/__init__.py         (  733 baris)  ← semua 53 SQLAlchemy models + DB setup
├── schemas/__init__.py        (1,138 baris)  ← semua 116 Pydantic schemas
├── routers/
│   ├── auth.py                (   98 baris)  ← 5 endpoint
│   ├── leads.py               (  827 baris)  ← 28 endpoint
│   ├── proposals.py           (  893 baris)  ← 19 endpoint
│   ├── finance.py             (  493 baris)  ← 21 endpoint
│   ├── clients.py             (  194 baris)  ←  4 endpoint
│   ├── workspace.py           (1,740 baris)  ← 25 endpoint
│   ├── documents.py           (1,137 baris)  ← 36 endpoint
│   ├── content.py             (  920 baris)  ← 37 endpoint
│   ├── settings.py            (  925 baris)  ← 26 endpoint
│   ├── campaign.py            (  763 baris)  ← 17 endpoint
│   ├── analytics.py           (  364 baris)  ←  9 endpoint
│   ├── office.py              (  227 baris)  ← 12 endpoint
│   └── other.py               (1,053 baris)  ← 32 endpoint (misc)
├── add_performance_indexes.sql  ← updated: 2 index baru
└── migrate.py                   ← unchanged
```

### 2. N+1 Query Fixes (di `routers/finance.py`, `routers/clients.py`, `routers/workspace.py`)

| Endpoint | Before | After | Improvement |
|----------|--------|-------|-------------|
| `GET /api/finance/transactions` | Query `Lead` per row (N+1) | `joinedload(Transaction.lead)` | **N queries → 1** |
| `GET /api/clients/{id}/activity-timeline` | Query `ProposalAnalytics` per proposal (N+1) | Bulk fetch + Python group | **N queries → 1** |
| `GET /api/workspace-list` | Query `Lead`, `Sheet`, `Rows`, `Columns`, `Cells` per project (5x N+1) | Bulk fetch all + `GROUP BY` aggregate | **5N queries → 5** |

### 3. Database Indexes (di `add_performance_indexes.sql`)

Index baru ditambahkan:
```sql
CREATE INDEX IF NOT EXISTS idx_documents_updated_at ON documents(updated_at);
CREATE INDEX IF NOT EXISTS idx_leads_archived_deleted ON leads(is_archived, deleted_at);
CREATE INDEX IF NOT EXISTS idx_board_cards_archived ON board_cards(is_archived);
```

### 4. Frontend Optimization (di `frontend/next.config.js`)

- `images.unoptimized: false` — Next.js image optimization aktif kembali
- `leaflet` dan `docx` sudah di-lazy-load dengan dynamic `import()` (sudah optimal sebelumnya)

---

## File yang Harus Di-upload ke Shared Hosting

Seluruh folder backend harus di-upload ulang karena struktur berubah total:

```
backend/
├── main.py                          ← UPDATE (berkurang dari 11,471 ke 206 baris)
├── models/__init__.py               ← NEW (pindahan dari main.py)
├── schemas/__init__.py              ← NEW (pindahan dari main.py)
├── routers/                         ← NEW (pindahan dari main.py)
│   ├── auth.py
│   ├── leads.py
│   ├── proposals.py
│   ├── finance.py
│   ├── clients.py
│   ├── workspace.py
│   ├── documents.py
│   ├── content.py
│   ├── settings.py
│   ├── campaign.py
│   ├── analytics.py
│   ├── office.py
│   └── other.py
├── add_performance_indexes.sql      ← UPDATE (index baru)
├── requirements.txt                 ← no change
├── passenger_wsgi.py                ← no change
├── migrate.py                       ← no change
├── migrate_add_columns.sql          ← no change
└── migrate_ai_proxies.sql           ← no change
```

**Cara deploy:**
1. Upload semua file di atas ke shared hosting (overwrite `main.py`, tambahkan folder `models/`, `schemas/`, `routers/`)
2. Jalankan index baru di production:
   ```bash
   mysql -h localhost -u USER -p DATABASE < add_performance_indexes.sql
   ```
3. Restart aplikasi (biasanya cukup touch `passenger_wsgi.py` atau restart Passenger)
4. Test: buka dashboard, buka invoice list, buka workspace — harus terasa lebih cepat

---

## Frontend (Vercel)

Tidak ada perubahan file frontend selain `next.config.js` yang sudah di-commit. Deploy seperti biasa via `git push`.

---

## Hasil yang Diharapkan

| Halaman | Sebelum | Sesudah |
|---------|---------|---------|
| Dashboard | 10-15s | 1-2s |
| Invoice list | 5-8s | 300-500ms |
| Invoice detail | 2-3s | 200-400ms |
| Customer list | 4-6s | 300ms |
| Workspace list | 5-10s | 500ms-1s |
| Initial page load | 3-5s | 1-2s |

---

## Kalau Masih Lambat Setelah Deploy

Kemungkinan bottleneck tersisa:
1. **Shared hosting resource limit** — CPU/disk I/O di server shared
2. **Network latency** — Frontend (Vercel Singapore) ke Backend (shared hosting — cek region)
3. **Frontend rendering** — React re-render berlebihan (Phase 2 optimization)

Debug: buka DevTools → Network tab → lihat request mana yang paling lambat → kirim screenshot.
