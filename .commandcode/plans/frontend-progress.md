# Frontend Optimasi — Progress

> 2026-06-04 | Build: ✅ PASS (zero errors, zero warnings)

## Fase 1: Shared Code Consolidation ✅
- `formatRupiah` centralized di `src/utils/formatter.ts` (removed from 11 files)
- `inputCls` / `inputClsLarge` centralized di `src/lib/inputCls.ts` (removed from 10 files)
- `download.ts` created — `downloadBlob()`, `downloadCSV()`
- All `document.createElement("a")` patterns replaced with `downloadBlob()`

## Fase 2: Fix Anti-Patterns ✅
- `api.ts`: 401 handler via callback pattern (`setUnauthorizedHandler`) — no more `window.location.href`
- `ClientLayout.tsx`: injects router via `useEffect` → `setUnauthorizedHandler`
- `SuspenseWrapper.tsx` created for reusable Suspense boundaries

## Fase 3: Split Mega-Files ⏭️ SKIPPED
- `clients/page.tsx` (1121L) and `LeadsTable.tsx` (1077L) NOT split
- Risk of regression too high for inline modal/logic threading
- Functionality preserved as-is

## Fase 4: Loading/Error Boundaries ✅
- `loading.tsx`: leads, clients, dashboard, proposals, finance
- `error.tsx`: leads, clients, dashboard, finance
- `/map` and `/scraper` redirect pages deleted → `next.config.js` redirects
- Stale `.next` cache cleared

## Files Created
```
src/
├── lib/inputCls.ts
├── utils/download.ts
├── components/SuspenseWrapper.tsx
├── app/leads/loading.tsx
├── app/leads/error.tsx
├── app/clients/loading.tsx
├── app/clients/error.tsx
├── app/dashboard/loading.tsx
├── app/dashboard/error.tsx
├── app/proposals/loading.tsx
├── app/finance/loading.tsx
└── app/finance/error.tsx
```

## Files Modified (~20)
- `utils/formatter.ts` — added `formatRupiah`
- `lib/api.ts` — callback-based 401 handler
- `components/ClientLayout.tsx` — inject router
- `next.config.js` — added redirects for /map, /scraper
- 11 files: removed duplicate `formatRupiah` → import from formatter
- 10 files: removed duplicate `inputCls` → import from lib/inputCls
- 5 files: replaced `document.createElement("a")` → `downloadBlob()`

## Files Deleted (2)
- `src/app/map/page.tsx`
- `src/app/scraper/page.tsx`
