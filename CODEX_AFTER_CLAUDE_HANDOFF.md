# Codex Handoff After Claude Waves

## Current Coordination

User has Codex GPT-5.5 High and Claude Code Sonnet 4.6. Claude can only run in 2 terminals max.

Do not start broad production fixes until user reports Claude wave results.

## Worktree Setup Already Done

Production blocker worktrees exist:

- `/home/kevin/kantorteman/.worktrees/fix-uploads` on branch `fix-production-uploads`
- `/home/kevin/kantorteman/.worktrees/fix-settings` on branch `fix-production-settings`
- `/home/kevin/kantorteman/.worktrees/fix-client-lead` on branch `fix-client-lead-integrity`
- `/home/kevin/kantorteman/.worktrees/fix-workspace` on branch `fix-workspace-board-sync`

Root repo has uncommitted/untracked work. Do not reset or discard anything.

Important audit file in root:

- `/home/kevin/kantorteman/PRODUCTION_AUDIT_MEMORY.md`

It is untracked in root, so Claude prompts reference it by absolute path.

## Team Split

Codex owns:

- Contact ID vs Lead ID data integrity
- Final integration/review/merge

Claude owns:

- Wave 1 Terminal 1: Upload path + document email/delete path
- Wave 1 Terminal 2: Settings destructive endpoints + backup
- Wave 2: Workspace-board sync + attachment auth, after one Claude terminal frees up

Do not use Claude for `fix-client-lead`; Codex should handle that because it is highest risk for data integrity.

## Current Codex State

Codex started investigating `fix-client-lead` but user interrupted before any code edits. Only read commands were run.

Relevant findings:

- Backend `GET /api/clients/detail/{client_id}` already returns `lead_id` in root response and in `profile.lead_id`.
- Backend project endpoints in `backend/routers/workspace.py` already accept `contact_id` and resolve it to `lead_id`.
- Frontend client detail still sends `lead_id: Number(clientId)` in `frontend/src/app/dashboard/clients/[client_id]/page.tsx`.
- `ProposalModal` sends `lead_id: contact.id` with `source: "contact"` for proposal creation, which backend can resolve, but unbilled warning calls `/api/finance/client/${contact.id}/unbilled`; that endpoint expects real `lead_id`.
- `FinancePanel` fetches `/api/contacts`, maps `id: c.id`, and stores it as transaction `lead_id`; this is wrong when `contact.id != lead.id`.
- Additional same-root issue found: client detail tabs use route `client_id` as `lead_id`:
  - `frontend/src/app/dashboard/clients/[client_id]/components/NotesTimelineTab.tsx`
  - `frontend/src/app/dashboard/clients/[client_id]/components/DocumentsTab.tsx`
  - `frontend/src/app/dashboard/clients/[client_id]/components/CredentialsTab.tsx`
  - parent `ClientTabs.tsx`

Expected direction:

- Pass canonical `lead_id` from client detail response into components that write/read lead-linked resources.
- For project creation from client detail, send `contact_id: Number(clientId)` or real `lead_id`, but never route `client_id` as `lead_id`.
- For finance client selector, use contacts' `lead_id` as the option value and ignore/disable contacts without `lead_id`.
- For proposal unbilled warning, use `contact.lead_id` when available. Proposal creation can keep `source: "contact"` with contact id, or switch to direct lead source only if backend/frontend contract remains clear.
- Add focused regression tests if feasible.

## What To Do After Claude Wave 1/2 Finishes

1. Ask user for Claude summaries or inspect these worktrees directly:
   - `.worktrees/fix-uploads`
   - `.worktrees/fix-settings`
   - `.worktrees/fix-workspace`
2. Review each diff before merging:
   - `git -C <worktree> status --short`
   - `git -C <worktree> diff --stat`
   - `git -C <worktree> diff`
3. Finish Codex-owned `fix-client-lead` in `.worktrees/fix-client-lead`.
4. Run targeted tests per worktree.
5. Integrate one worktree at a time into root only after review.
6. Clean debug artifacts before production push:
   - `Parse`
   - `Run`
   - `Show`
   - `Use`
   - `YES`
   - `backend/tests/test_debug_proposal.py`
   - `backend/tests/test_direct_accept.py`
   - likely `frontend/tsconfig.tsbuildinfo` if it is just a build artifact
7. Update `/home/kevin/kantorteman/PRODUCTION_AUDIT_MEMORY.md` with final blocker status.
8. Do not push production until all blockers are closed or user explicitly accepts a risk.

## Never Do

- Do not run seed/reset/demo on production data.
- Do not discard unrelated root changes.
- Do not assume localhost cookie behavior matches production.
- Do not push until final integration and verification are done.
