# feat/frontend-phase3 — Task List

> Branch: `feat/frontend-phase3` | Worktree: `kantorteman/.worktrees/frontend`
> Target: Split 8 mega-files + full SWR migration

---

## ⚠️ Critical Rules

- **Build pass tiap commit**: `npm run build`
- **Mobile + dark mode**: harus tetap jalan
- **Commit**: 1 file = 1 commit (kecuali terkait)
- **Jangan ubah behavior**: CRUD, filter, modal, toast identik

---

## Task 1: Split content-generator (1363L)

Extract ke `frontend/src/components/content/`:
- `ContentForm.tsx` — platform/format/tone input (~200L)
- `ContentPreview.tsx` — preview hasil generasi (~200L)
- `ContentHistory.tsx` — history sidebar (~180L)
- `ContentScheduler.tsx` — schedule post (~150L)
- Page jadi ~60L orchestrator

## Task 2: Split chat page (1156L)

Extract ke `frontend/src/components/chat/`:
- `ChatInput.tsx` — input box + send (~120L)
- `ChatMessageList.tsx` — list render + auto-scroll (~200L)
- `ChatMessageBubble.tsx` — single message (~100L)
- `ChatHistory.tsx` — sidebar conversations (~150L)
- `ChatProviderPicker.tsx` — AI provider selector (~80L)
- Page jadi ~60L

## Task 3: Split documents pages (1122L + 1379L)

### 3a. docs/page.tsx → `frontend/src/components/documents/DocumentsList.tsx` (~400L)

### 3b. documents/generator/new/page.tsx → `frontend/src/components/documents/`
- `DocumentGenerator.tsx` — main form (~400L)
- `DocumentPreview.tsx` — preview panel (~300L)
- `DocumentVariables.tsx` — variable input (~200L)

## Task 4: Split board page (928L)

Extract ke `frontend/src/components/board/`:
- `BoardColumn.tsx` — single column (~150L)
- `BoardCard.tsx` — single card (~200L)
- `BoardHeader.tsx` — filters + actions (~120L)
- `CardDetailModal.tsx` — card detail + checklist (~250L)
- Page jadi ~80L

## Task 5: Split report + proposal pages

### 5a. report/[slug]/page.tsx (859L) → `ReportChart.tsx` + `ReportTable.tsx` (~300L each)
### 5b. proposal/[id]/page.tsx (830L) → `ProposalPreview.tsx` + `ProposalActions.tsx` (~300L each)
### 5c. ClientTabs.tsx (688L) → `ClientProfileTab.tsx` + `ClientProjectsTab.tsx` + `ClientFinanceTab.tsx` (~200L each)

## Task 6: Migrasi SWR ke sisa halaman

- content-generator → `useApi` untuk fetch templates + history
- chat → `useApi` untuk conversations
- documents → `useApi` untuk document list
- board → `useApi` untuk board + cards
- settings → `useApi` untuk settings data

## Task 7: Cleanup & Verify

- `npm run build` + `npx tsc --noEmit` zero errors
- Hapus dead code
- Test 5 halaman utama
- Merge ke main

---

**Prioritas**: Task 1 → 2 → 3 → 4 → 5 → 6 (paling berat dulu)
