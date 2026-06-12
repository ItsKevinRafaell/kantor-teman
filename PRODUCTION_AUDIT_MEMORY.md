# Production Audit Memory - 2026-06-11

## Context
User wants a full production-readiness audit before pushing. Production data will be real, so do not push until all modules are clean. Features that are not safe or not important can be pending locally, but the user selected "semua modul" as the required production scope for now.

Important user decisions:
- Production push scope: all modules must be clean before push.
- Shared hosting environment: final env/path values will be shared later by user.
- Data safety: reset/seed demo must be disabled in production.

## Current Verdict
Production-readiness blockers from this memo have been addressed in the local final integration pass. Re-verified on 2026-06-11 with targeted backend P0/hardening/campaign suites, frontend TypeScript check, and Next production build.

Residual risk:
- `backend/tests/test_security.py` hung without output and was killed.
- `backend/tests/test_finance.py` and `backend/tests/test_api_contracts.py` still time out at 120 seconds, matching prior audit history.
- Browser audit used empty local data, so it verified navigation/render/empty states rather than live production workflows with real records.
- `npm run build` exits 0, but static generation logs `ECONNREFUSED 127.0.0.1:8000` when local API is not running. This is a local build-time fetch warning, not a compile failure.
- Deploy environment values and production smoke with real shared-hosting records still must be verified before push/deploy.

## Looks Mostly Ready, Re-verify Only
- Webhook Fonnte read/reply: backend supports incoming JSON/form, secret via header/query/body, dual phone matching, opt-out, reply status, follow-up stop, and activity logging. P0 tests passed.
- AI Engine: multi-provider configs exist for OpenAI, Anthropic, Gemini, OpenRouter, and custom providers. P0 tests passed.
- Document Generator variable source: backend preview/generate uses input `variables` as source of truth; frontend sends input field values. P0 tests passed.
- Proposal page: "Tambah Proposal" stays on page with modal and client search.
- Client and detail client proposal form reuse same `ProposalModal` component.
- Breadcrumb/back buttons appear implemented on main pages.
- Content Generator duplicate nav looks resolved; internal sidebar is clickable and breadcrumb changes per tool.
- Board color defaults and legacy board color mapping are more neutral/minimal.

## Production Blockers

Final status after integration:
- Contact ID vs Lead ID data integrity: fixed.
- Workspace-board sync: fixed and covered by regression tests.
- Upload path consistency: fixed.
- Workspace attachment upload auth: fixed.
- Document download/email/delete path: fixed for both generated document filename style and `/uploads/documents/...` URL style, covered by regression tests.
- Settings destructive endpoints in production: fixed and covered by regression tests. Backup endpoint NameError was fixed by importing `DATABASE_URL` from config and adding backup coverage.
- Production environment values: code is aligned; deploy env still must be set on hosting.

### 1. Contact ID vs Lead ID data integrity
Several frontend flows still confuse `contact.id` and `lead.id`.

Known locations:
- `frontend/src/app/dashboard/clients/[client_id]/page.tsx`
  - `saveProject()` sends `lead_id: Number(clientId)`.
  - Route param `client_id` is a contact ID, not guaranteed to be lead ID.
  - This can link projects to the wrong lead or fail with "Lead tidak ditemukan".
- `frontend/src/components/clients/ProposalModal.tsx`
  - Proposal creation itself can resolve contact via `source: "contact"`, but unbilled warning calls `/api/finance/client/${contact.id}/unbilled`.
  - Backend expects `lead_id`, so dana talangan warning can be wrong/missing.
- `frontend/src/components/finance/FinancePanel.tsx`
  - Fetches `/api/contacts`, maps `id: c.id`, then stores that as transaction `lead_id`.
  - Backend `Transaction.lead_id` points to `leads.id`.
  - This can store wrong links or fail if FK enforcement catches it.

Required fix:
- Use a canonical client DTO that exposes both `contact_id` and `lead_id`, or resolve contact to lead server-side for every endpoint that accepts client/contact input.
- Update project creation, finance transaction linking, and unbilled warning to use actual `lead_id`.

### 2. Workspace-board sync is incomplete
`backend/routers/workspace.py` imports `sync_row_to_board` from `backend/app/core/dependencies.py`.

Problem:
- `sync_row_to_board()` returns early if `not board or not row.board_card_id`.
- New workspace rows do not get a board card created or linked.
- Some sync keys expect `task` / `deadline`, while templates use keys like `task_name` / `due_date`.

Required fix:
- Make sync create/link a `BoardCard` when a row has no `board_card_id`.
- Sync title, deadline, and status using actual workspace template column keys.
- Keep workspace status options dynamically derived from board columns.
- Add regression tests for row creation, status update, title/deadline sync, and board card linkage.

### 3. Upload paths are inconsistent
Backend writes uploads using `backend/app/core/dependencies.py`:
- `UPLOADS_DIR = backend/app/uploads`

But FastAPI static server in `backend/main.py` serves:
- `backend/uploads`

Impact:
- Files can be written successfully but not served from `/uploads`.
- Affects brand kit, workspace attachments, document generated files, and backups.

Required fix:
- Define one canonical uploads directory shared by writers, static mount, document services, workspace attachments, and backups.
- Ensure `/uploads/...` URLs point to the same physical directory.
- Preserve existing production files during migration/copy.

### 4. Workspace attachment upload auth is broken
`frontend/src/components/workspace/WorkspaceSheet.tsx` uses:
- raw `fetch()`
- manual Authorization header from `document.cookie`

Problem:
- Auth cookie `kt_token` is HttpOnly, so JS cannot read it.
- Request also lacks `credentials: "include"`.

Required fix:
- Use the same auth behavior as `apiFetch`, or raw `fetch` with `credentials: "include"` and no manual cookie parsing.
- Verify upload succeeds in production cookie/domain setup.

### 5. Document email/delete file path bug
`backend/routers/documents.py` email endpoint builds file path from router directory:
- `os.path.join(os.path.dirname(__file__), doc.file_url.lstrip("/"))`

Problem:
- Generated documents live under `DOCUMENTS_DIR`, not `backend/routers/...`.
- Email can return "File tidak ada di disk".
- Delete physical file path has similar risk.

Required fix:
- Resolve document files via canonical uploads/generated documents path.
- Add tests for download, email path lookup, and delete physical file cleanup.

### 6. Settings destructive endpoints are unsafe for production
Known issues in `backend/routers/settings.py`:
- Legacy `/api/admin/seed` only requires admin and can mutate production data.
- `/api/admin/data/reset-soft` claims to preserve clients but deletes all `Contact`.
- `/api/admin/data/seed-demo` references demo seed objects that may not be imported and may 500.
- Backup currently risks missing uploads because uploads path is inconsistent.

Required fix:
- In production, block destructive seed/reset/demo endpoints at backend level.
- UI should show clear explanation that these actions are disabled in production.
- Backup must include DB plus canonical uploads directory.
- Soft reset wording and behavior must match; never delete real clients if it says clients are preserved.

### 7. Production environment is not locked yet
Current known config:
- `frontend/.env.production`: `NEXT_PUBLIC_API_URL=https://api.kantorteman.my.id`
- `frontend/next.config.js`: CSP/connect-src and rewrites assume `https://api.kantorteman.my.id`
- `backend/passenger_wsgi.py` hardcodes `/home/qqwtlphb/backend` and Python 3.13 venv path.
- Backend auth cookie domain is `.kantorteman.my.id`.

Required fix after user shares env:
- Align frontend URL, API URL, CORS, cookie domain, Passenger path, Python version/venv path, and uploads path.
- Local must mimic production domain/cookie behavior, not only localhost.

## Tests Already Run
- Final local integration verification on 2026-06-11:
  - `rtk python -m py_compile backend/routers/settings.py backend/routers/documents.py backend/routers/workspace.py backend/app/core/dependencies.py`
    - Passed.
  - `rtk pytest -q backend/tests/test_hardening.py::HardeningRegressionTests -k "upload_path or email_document or delete_generated or uploads_documents or backup"`
    - 4 passed.
  - `rtk pytest -q backend/tests/test_hardening.py::ProductionGuardTests`
    - 7 passed.
  - `rtk pytest -q backend/tests/test_p0_fixes.py::TestWorkspaceBoardSync`
    - 5 passed.
  - `rtk pytest -q backend/tests/test_p0_fixes.py`
    - 99 passed.
  - `rtk pytest -q backend/tests/test_hardening.py`
    - 24 passed.
  - `rtk pytest -q backend/tests/test_campaign.py`
    - 6 passed.
  - `cd frontend && rtk ./node_modules/.bin/tsc --noEmit --incremental false`
    - Passed.
  - `cd frontend && rtk npm run build`
    - Passed. Build logged local API `ECONNREFUSED 127.0.0.1:8000`, but exited 0.

Earlier verification:
- `cd frontend && ./node_modules/.bin/tsc --noEmit --incremental false`
  - Passed.
- `pytest -q backend/tests/test_p0_fixes.py`
  - 89 passed.
- `pytest -q backend/tests/test_campaign.py`
  - 6 passed.
- `pytest -q backend/tests/test_hardening.py`
  - 1 failed, 12 passed.
  - Failure: `test_document_vars_do_not_replace_defaults_with_empty_strings`.
  - This test appears stale because new requirement says Document Generator pulls from input fields, and empty string input should remain empty.
- Full backend tests with debug tests ignored timed out.
- `backend/tests/test_finance.py` and `backend/tests/test_api_contracts.py` hung for more than 2 minutes and were killed.

## Release Hygiene
Final integration removed these debug artifacts from the root working tree:
- `Parse`
- `Run`
- `Show`
- `Use`
- `YES`
- `backend/tests/test_debug_proposal.py`
- `backend/tests/test_direct_accept.py`

Still verify whether `frontend/tsconfig.tsbuildinfo` should be committed. It appears to be a typecheck/build artifact and was already modified in the root worktree before final integration.

## Recommended Fix Order
1. Fix canonical upload path and production backup coverage.
2. Disable production destructive settings endpoints.
3. Fix contact/lead ID mapping across client detail, proposal unbilled, and finance.
4. Fix workspace-board row/card sync and attachment auth.
5. Fix document email/delete file path.
6. Clean debug artifacts and stale tests.
7. Re-run frontend typecheck and backend targeted/full suites.
8. Apply final shared-hosting env values from user.
9. Only then commit/push production-ready changes.

## Do Not Assume
- Do not assume current `CLAUDE.md` statement "production ready" is true.
- Do not assume localhost cookie behavior matches production.
- Do not run seed/reset/demo on production data.
- Do not upload local DB, local uploads, or local `.env` to production unless explicitly requested.

## Ecosystem Integration Execution - 2026-06-11 15:49 WIB

Kevin requested final integration matrix and execution in this order:
1. TemanUMKMKita lead intake.
2. AutoLead demo bridge.
3. Office-Hermes permanent endpoint.
4. Office command center read/actions.

Implemented locally, no deploy/push/seed/reset/production mutation:
- Added root ecosystem matrix: `/home/kevin/ECOSYSTEM_INTEGRATION_MATRIX.md`.
- KantorTeman source-of-truth status contract:
  - `backend/routers/integrations.py`
  - registered in `backend/main.py`
  - endpoint: `/api/integrations/ecosystem/status`
  - reports lead-intake, AutoLead, and Hermes config state without exposing secrets.
- Added KantorTeman regression:
  - `backend/tests/test_ecosystem_integrations.py`

Cross-project changes outside KantorTeman:
- TemanUMKMKita:
  - `backend/app/routers/contact.py`
  - `backend/tests/test_contact_integration.py`
  - `docs/kantorteman-lead-intake.md`
- AutoLead / LeadBot:
  - `.env.example`
  - `package.json`
  - `scripts/smoke-kantorteman-bridge.js`
  - `src/config.js`
  - `src/routes/webhook.js`
  - `docs/KANTORTEMAN_BRIDGE.md`
- OfficeKantorTeman:
  - `.env.example`
  - `MEMORY.md`
  - `app/api/proxy/[...path]/route.ts`
  - `app/api/ecosystem/status/route.ts`
  - `app/api/ecosystem/actions/route.ts`
  - `app/lib/api/ecosystem.ts`
  - `app/lib/api.ts`
  - `app/types/ecosystem.ts`
  - `app/types/index.ts`
  - `app/components/work/WorkMode.tsx`
  - `docs/office-hermes-permanent-endpoint.md`
  - `docs/ecosystem-command-center.md`

Verification passed:
- `cd /home/kevin/temanumkmkita && rtk pytest -q backend/tests/test_contact_integration.py`
  - 2 passed.
- `cd /home/kevin/kantorteman && rtk pytest -q backend/tests/test_ecosystem_integrations.py backend/tests/test_whatsapp_provider.py`
  - 5 passed.
- `cd /home/kevin/kantorteman && rtk pytest -q backend/tests/test_p0_fixes.py`
  - 99 passed.
- `cd /home/kevin/kantorteman && rtk pytest -q backend/tests/test_hardening.py`
  - 24 passed.
- `cd /home/kevin/kantorteman && rtk pytest -q backend/tests/test_campaign.py`
  - 6 passed.
- `cd /home/kevin/kantorteman/frontend && rtk ./node_modules/.bin/tsc --noEmit --incremental false`
  - Passed.
- `cd /home/kevin/kantorteman/frontend && rtk npm run build`
  - Passed; known local API `ECONNREFUSED 127.0.0.1:8000` still logged but exit code was 0.
- `cd /home/kevin/officekantorteman && rtk ./node_modules/.bin/tsc --noEmit --incremental false`
  - Passed.
- `cd /home/kevin/officekantorteman && rtk npm run build`
  - Passed.
- `cd /home/kevin/leadbot_remote_work && rtk node --check src/config.js && rtk node --check src/routes/webhook.js && rtk node --check scripts/smoke-kantorteman-bridge.js`
  - Passed.

Remaining risks:
- Production env values are not confirmed in this session.
- Live health/smoke checks were not run because they require real tokens/domains and Kevin approval.
- `office.kantorteman.my.id` still needs DNS/reverse proxy/TLS setup to `127.0.0.1:18100` on VPS.
- AutoLead path is not a git worktree at `/home/kevin/leadbot_remote_work`, so file-level handoff is required before deployment.
- Root worktrees remain dirty with unrelated/pre-existing changes; do not reset/discard.

Exact next step:
- Kevin confirms production env values and approves live smoke/deploy order. Then run read-only health checks first, followed by approved AutoLead demo send only if `AUTOLEAD_SMOKE_SEND=true` is explicitly allowed.
