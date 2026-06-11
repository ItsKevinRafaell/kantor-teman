# Claude Parallel Production Fix Prompts

## Cara Pakai

Jalankan Claude Code dari terminal repo utama:

```bash
cd /home/kevin/kantorteman
claude
```

Paste prompt **Orchestrator** di bawah ke tab Claude pertama.

Setelah dia selesai membuat worktree, buka 4 terminal baru dan jalankan Claude di masing-masing folder yang dia buat:

```bash
cd /home/kevin/kantorteman/.worktrees/fix-uploads && claude
cd /home/kevin/kantorteman/.worktrees/fix-settings && claude
cd /home/kevin/kantorteman/.worktrees/fix-client-lead && claude
cd /home/kevin/kantorteman/.worktrees/fix-workspace && claude
```

Paste prompt task yang sesuai ke masing-masing tab.

## Prompt 1 - Orchestrator

```text
Kamu adalah orchestrator untuk production-readiness repo Kantor Teman.

Kerja dari root repo utama. Jangan edit source app di root kecuali user minta integrasi final. Tugas awalmu hanya:

1. Baca PRODUCTION_AUDIT_MEMORY.md.
2. Cek git status.
3. Buat worktree paralel berikut jika belum ada:
   - .worktrees/fix-uploads branch fix/production-uploads
   - .worktrees/fix-settings branch fix/production-settings
   - .worktrees/fix-client-lead branch fix/client-lead-integrity
   - .worktrees/fix-workspace branch fix/workspace-board-sync
4. Kalau branch/worktree sudah ada, jangan overwrite. Laporkan statusnya.
5. Jangan hapus untracked files dan jangan reset perubahan user.
6. Setelah setup, tampilkan command terminal yang harus dibuka user untuk tiap worktree.

Perintah yang boleh kamu jalankan:
- git status --short
- git branch --list
- git worktree list
- mkdir -p .worktrees
- git worktree add sesuai branch di atas

Jangan mulai memperbaiki blocker di tab orchestrator ini.
```

## Prompt 2 - Uploads + Documents

Run di:

```bash
cd /home/kevin/kantorteman/.worktrees/fix-uploads
claude
```

Paste:

```text
Kamu bekerja di worktree fix/production-uploads untuk repo Kantor Teman.

Baca PRODUCTION_AUDIT_MEMORY.md. Fokus hanya blocker:
- Upload paths are inconsistent
- Document email/delete file path bug

Jangan sentuh module lain kecuali perlu langsung untuk blocker ini.

Target:
1. Jadikan satu canonical uploads directory yang dipakai writer dan static mount.
2. Pastikan /uploads/... URL menunjuk physical directory yang sama.
3. Perbaiki document email endpoint dan delete physical file supaya resolve file dari canonical uploads/generated documents path, bukan dari backend/routers.
4. Preserve existing production files secara konsep. Jangan buat migrasi destruktif.
5. Tambahkan/ubah regression tests untuk download/email/delete path bila test infra memungkinkan.

Larangan:
- Jangan jalankan seed/reset/demo.
- Jangan push.
- Jangan commit sebelum user/integrator review.

Setelah selesai:
- Jalankan targeted pytest yang relevan.
- Beri ringkasan file berubah, behavior berubah, dan test result.
```

## Prompt 3 - Settings + Backup

Run di:

```bash
cd /home/kevin/kantorteman/.worktrees/fix-settings
claude
```

Paste:

```text
Kamu bekerja di worktree fix/production-settings untuk repo Kantor Teman.

Baca PRODUCTION_AUDIT_MEMORY.md. Fokus hanya blocker:
- Settings destructive endpoints are unsafe for production
- Backup must include canonical uploads directory bila path helper sudah tersedia

Target:
1. Di production, backend harus block destructive seed/reset/demo endpoints.
2. /api/admin/seed, /api/admin/data/reset-soft, /api/admin/data/seed-demo jangan bisa mutate production.
3. Soft reset wording dan behavior harus sesuai. Kalau klaim preserve clients, jangan delete Contact.
4. UI settings harus menjelaskan action destructive disabled di production.
5. Backup harus mencakup database + uploads directory canonical jika helper sudah ada. Kalau helper belum ada, buat integrasi minimal tanpa konflik besar.
6. Tambahkan tests untuk production guard destructive endpoints.

Larangan:
- Jangan jalankan seed/reset/demo.
- Jangan push.
- Jangan commit sebelum user/integrator review.

Setelah selesai:
- Jalankan targeted pytest settings/hardening.
- Beri ringkasan file berubah, behavior berubah, dan test result.
```

## Prompt 4 - Contact ID vs Lead ID

Run di:

```bash
cd /home/kevin/kantorteman/.worktrees/fix-client-lead
claude
```

Paste:

```text
Kamu bekerja di worktree fix/client-lead-integrity untuk repo Kantor Teman.

Baca PRODUCTION_AUDIT_MEMORY.md. Fokus hanya blocker:
- Contact ID vs Lead ID data integrity

Known locations:
- frontend/src/app/dashboard/clients/[client_id]/page.tsx
- frontend/src/components/clients/ProposalModal.tsx
- frontend/src/components/finance/FinancePanel.tsx

Target:
1. Jangan pakai contact.id sebagai lead_id.
2. Project creation dari client detail harus resolve/use actual lead_id.
3. Proposal unbilled warning harus call backend dengan lead_id yang benar atau endpoint backend menerima contact safely.
4. Finance transaction linking harus simpan Transaction.lead_id berdasarkan leads.id, bukan contacts.id.
5. Prefer solusi canonical DTO yang expose contact_id dan lead_id, atau server-side resolution yang konsisten.
6. Tambahkan tests bila ada pattern backend/frontend test yang cocok.

Larangan:
- Jangan ubah UX besar.
- Jangan push.
- Jangan commit sebelum user/integrator review.

Setelah selesai:
- Jalankan frontend tsc.
- Jalankan targeted backend tests terkait finance/proposal/client jika ada.
- Beri ringkasan file berubah, behavior berubah, test result, dan risiko migrasi data lama kalau ditemukan.
```

## Prompt 5 - Workspace

Run di:

```bash
cd /home/kevin/kantorteman/.worktrees/fix-workspace
claude
```

Paste:

```text
Kamu bekerja di worktree fix/workspace-board-sync untuk repo Kantor Teman.

Baca PRODUCTION_AUDIT_MEMORY.md. Fokus hanya blocker:
- Workspace-board sync is incomplete
- Workspace attachment upload auth is broken

Target:
1. sync_row_to_board harus create/link BoardCard ketika row belum punya board_card_id.
2. Sync title, deadline, status pakai actual workspace template column keys, termasuk variasi task_name/due_date.
3. Workspace status options tetap derive dari board columns.
4. Attachment upload frontend jangan baca kt_token dari document.cookie karena HttpOnly. Pakai apiFetch behavior atau fetch credentials: "include".
5. Tambahkan regression tests untuk row creation, status update, title/deadline sync, dan board_card_id linkage bila test infra memungkinkan.

Catatan:
- Kalau file canonical upload helper sedang disentuh branch lain, jangan refactor upload path di task ini. Fokus auth fetch saja untuk attachment.

Larangan:
- Jangan push.
- Jangan commit sebelum user/integrator review.

Setelah selesai:
- Jalankan targeted workspace tests.
- Beri ringkasan file berubah, behavior berubah, dan test result.
```

## Prompt 6 - Integrasi Final

Run di root repo utama setelah semua tab task selesai:

```bash
cd /home/kevin/kantorteman
claude
```

Paste:

```text
Kamu adalah integrator production-readiness Kantor Teman.

Baca PRODUCTION_AUDIT_MEMORY.md dan review hasil worktree:
- .worktrees/fix-uploads
- .worktrees/fix-settings
- .worktrees/fix-client-lead
- .worktrees/fix-workspace

Tugas:
1. Review diff tiap worktree.
2. Cari konflik, regression, overlap file, dan solusi yang setengah matang.
3. Jangan merge otomatis kalau test gagal atau ada konflik konseptual.
4. Kalau aman, merge/cherry-pick perubahan satu per satu ke root main.
5. Bersihkan debug artifacts:
   - Parse, Run, Show, Use, YES
   - backend/tests/test_debug_proposal.py
   - backend/tests/test_direct_accept.py
   - frontend/tsconfig.tsbuildinfo kalau artifact
6. Run final:
   - frontend typecheck/build sesuai repo
   - backend targeted tests
   - full backend tests jika tidak hang; kalau hang, laporkan test mana.
7. Update PRODUCTION_AUDIT_MEMORY.md dengan status final.

Larangan:
- Jangan push production sebelum semua blocker closed atau user explicitly accept risk.
- Jangan jalankan seed/reset/demo.
- Jangan revert unrelated user changes.
```
