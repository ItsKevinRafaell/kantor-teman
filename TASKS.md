# feat/frontend-optimize — Phase 2: Selesaikan yang mangkrak

> Branch: `feat/frontend-optimize` | Worktree: frontend

## ⚠️ Rules
- Build pass tiap commit
- Mobile + dark mode tetap jalan
- Commit 1 task = 1 commit

---

## Task 1: Migrasi SWR di dashboard + leads
- Ganti `useState + useEffect + apiFetch` jadi `useApi` di 2 halaman
- Dashboard: fetch summary pakai SWR caching
- Leads page: fetch leads + batches pakai SWR

## Task 2: Split LeadsTable state management  
- Ekstrak state polling + fetch logic dari LeadsTable ke custom hook `useLeadsTable`
- LeadsTable.tsx jadi ~300L (view only + panggil hook)

## Task 3: Split client detail page
- `dashboard/clients/[client_id]/page.tsx` = 1159L
- Ekstrak jadi: `ClientProfile.tsx`, `ClientProjects.tsx`, `ClientCredentials.tsx`, `ClientNotes.tsx`
- Page jadi thin wrapper ~50L

---

Kalau selesai → merge ke main.
