# feat/frontend-optimize — Task List

> Branch: `feat/frontend-optimize` | Worktree: `/home/kevin/kantorteman/.worktrees/frontend`
> Target: Optimasi struktural — types, auth, SWR, hooks, split mega-files
> Deadline: secepatnya, yang penting benar

---

## ⚠️ Critical Rules

- **Mobile responsive**: semua pattern `sm:`, `max-w-`, `px-2.5 py-1.5 sm:px-4` harus tetap jalan
- **Dark mode**: semua komponen harus support `dark:` variant
- **Zero functionality loss**: CRUD, filter, modal, toast harus identik
- **Build**: `npm run build` harus pass tiap selesai 1 task
- **Commit**: 1 task = 1 commit

---

## Task 1: Shared Types Directory

**File baru**: `frontend/src/types/`
```
types/
├── index.ts        — barrel export
├── contact.ts      — Contact, ProjectData, ServiceItem, ProductItem
├── lead.ts         — Lead, LeadStatus, LeadMap
├── finance.ts      — WalletData, TransactionData, ReportData, SubscriptionData
├── proposal.ts     — ProposalRecord, TimelinePhase
└── campaign.ts     — Campaign, ProviderData, CampaignCost
```

Extract semua interface inline dari komponen ke `types/`. Ganti import ke `@/types`.

**Verifikasi**: `npx tsc --noEmit` zero errors
**Commit**: `feat(frontend): extract shared TypeScript types`

---

## Task 2: Auth Context

**File baru**: `frontend/src/contexts/AuthContext.tsx`

- `AuthProvider` — baca cookie + localStorage di mount, expose `user`, `role`, `isAdmin`, `login()`, `logout()`
- `useAuth()` hook — ganti semua `getUserInfo()` di komponen
- Auth state reactive — nggak perlu refresh halaman

**Files**: `ClientLayout.tsx`, `Sidebar.tsx`, `TopBar.tsx`, `AdminGuard.tsx`, `useUserRole.ts`
**Verifikasi**: login → dashboard tampil nama → sidebar menu sesuai role → logout redirect /login
**Commit**: `feat(frontend): add AuthContext replacing localStorage auth`

---

## Task 3: SWR Data Fetching

**Install**: `npm install swr`

**File baru**: `frontend/src/lib/swr.ts`
- `useApi<T>(path)` — wrapper `useSWR` + `apiFetchJson`
- `apiMutate(path)` — optimistic update

**Migrate bertahap**: dashboard → leads → clients → proposals
**Verifikasi**: data tetap muncul, loading state via `isValidating`
**Commit**: 1 commit per halaman

---

## Task 4: Custom Hooks

**File baru**: `frontend/src/hooks/`
```
hooks/
├── usePolling.ts    — generic polling (ganti setInterval manual)
├── useToast.ts      — toast state + auto-dismiss
├── useModal.ts      — modal open/close/data state
└── useDebounce.ts   — debounce input search
```

**Commit**: `feat(frontend): add reusable hooks`

---

## Task 5: Split Mega-Files — Clients Page

Extract ke `frontend/src/components/clients/`:
- `ClientsTable.tsx` — tabel + search/sort (~120L)
- `ClientsTableRow.tsx` — single row (~100L)
- `AddClientModal.tsx` — form (~60L)
- `EditClientModal.tsx` — form (~60L)
- `ClientDetailModal.tsx` — tabs (~120L)
- `ProjectModal.tsx` — add/edit project (~140L)
- `NotesModal.tsx` — 3-kolom notes (~100L)
- `ProposalModal.tsx` — service select + timeline (~180L)
- `ClientModals.tsx` — orchestrator (~40L)

**PENTING**: Split 1 modal per commit. Jangan sekaligus. Kalau error → revert commit itu.

---

## Task 6: Split Mega-Files — LeadsTable

Extract ke `frontend/src/components/leads/`:
- `LeadsFilterBar.tsx` — filter status/batch/rating (~100L)
- `LeadsTableRow.tsx` — single row + actions (~200L)
- `LeadsSearchActions.tsx` — search + add + export (~40L)
- `SalesModal.tsx` — follow-up form (~60L)
- `FollowUpModal.tsx` — template selector (~60L)
- `WaPreviewModal.tsx` — WA preview (~60L)
- `BlastModal.tsx` — batch blast (~130L)
- `LeadsModals.tsx` — orchestrator (~40L)
- `LeadsTableCore.tsx` — filtered/paginated table (~120L)

---

## Task 7: Cleanup

- Hapus `ConfirmModal.tsx` kalau sudah nggak dipakai
- `npm run build` + `npx tsc --noEmit` zero errors
- Test: dashboard, leads, clients, finance, proposals
- Merge ke `main`

**Commit**: `chore(frontend): cleanup dead code after structural refactor`
