# Frontend Kantorteman — Optimasi 4 Fase

> Audit: 2026-06-04 | Prinsip: Zero functionality loss. No UX changes.

---

## Temuan Audit

### 2 Mega-file (>1000 baris)
- `src/app/clients/page.tsx` — 1,128L
- `src/components/LeadsTable.tsx` — 1,078L

### Duplikasi
- `formatRupiah` di 6+ file
- `inputCls` (CSS class string) di semua komponen CRUD
- Modal inline di 7+ komponen — Modal.tsx ada tapi kurang dipakai
- `StarRating` di 2 tempat
- CSV download via `document.createElement("a")` di 2 tempat

### Anti-pattern
- Semua 37 halaman "use client" — zero server components
- `window.location.href` untuk redirect
- `useSearchParams` tanpa Suspense di beberapa halaman
- Zero loading.tsx / error.tsx
- Zero types/ directory
- setInterval polling terpisah di banyak komponen

---

## Fase 1: Shared Code Consolidation

**Tujuan**: Eliminasi duplikasi. Zero behavioral changes.

### Actions
1. `formatRupiah` → `src/utils/formatter.ts` (reuse dari yang sudah ada)
2. `src/lib/inputCls.ts` — export inputCls constant
3. `src/types/` — contact, project, proposal, lead, finance types
4. `src/utils/download.ts` — downloadCSV/downloadBlob
5. Replace semua duplikasi di 15+ file

**Verifikasi**: `npm run build` sukses, zero TS errors.

---

## Fase 2: Fix Anti-Patterns

**Tujuan**: Perbaiki architectural issues tanpa ubah struktur.

### Actions
1. `window.location.href` → callback pattern di api.ts + ClientLayout inject
2. Suspense-wrapper untuk useSearchParams di semua halaman
3. Sidebar direct fetch → apiFetch()
4. ConfirmModal → Modal (board/page.tsx)
5. LeadsMap inline StarRating → import dari StarRating.tsx

**Verifikasi**: Build + smoke test (login, leads, finance tabs).

---

## Fase 3: Split Mega-Files

**Tujuan**: Pecah clients/page.tsx dan LeadsTable.tsx jadi komponen focused.

### 3a. `clients/page.tsx` (1128L → ~200L)
Komponen baru di `src/components/clients/`:
- ClientsTable, ClientsTableRow, AddClientModal, EditClientModal
- ClientDetailModal, ProjectModal, NotesModal, ProposalModal, ClientModals

### 3b. `LeadsTable.tsx` (1078L → ~200L)
Komponen tambahan di `src/components/leads/`:
- LeadsFilterBar, LeadsTableRow, LeadsSearchActions
- SalesModal, FollowUpModal, WaPreviewModal, BlastModal
- LeadsModals, LeadsTableCore

### 3c. Extract `FormModal.tsx` untuk shared form pattern

**Verifikasi**: Full regression — semua modal, action, filter, pagination, mobile responsive.

---

## Fase 4: Loading, Error Boundaries & Polish

**Tujuan**: Tambah loading.tsx, error.tsx, konsolidasi skeleton.

### Actions
1. loading.tsx: leads, clients, dashboard, proposals, finance
2. error.tsx: leads, clients, dashboard, finance
3. Skeleton.tsx shared component (TableSkeleton, CardSkeleton)
4. Redirect pages: ganti /map dan /scraper dengan next.config redirects
5. Optional: hooks/usePolling, useToast, useModal

**Verifikasi**: API failure → error.tsx. Navigasi → loading skeleton.

---

## Ringkasan

| Fase | Risk | Files Create | Files Modify | Files Delete |
|---|---|---|---|---|
| 1: Consolidation | Low | ~8 | ~15 | 0 |
| 2: Anti-patterns | Low-Med | 1 | ~8 | 1 |
| 3: Mega-files | Med-High | ~19 | 3 | 0 |
| 4: Boundaries | Low | ~9 | ~3 | 2 |

**Total**: ~37 baru, ~29 modifikasi, 3 dihapus.

Tidak ada dependency baru. Mobile responsive preserved. Setiap fase deployable independen.
