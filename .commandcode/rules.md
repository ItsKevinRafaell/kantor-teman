# Kantorteman — Development Rules

## Repository Structure
- Monorepo: `backend/` (FastAPI), `frontend/` (Next.js), `hermes-gateway/` (numpang, aplikasi terpisah)
- `main` branch: protected, hanya terima merge dari feature branch
- Semua kerja di feature branch: `feat/<domain>-<deskripsi>`

## Branch Naming
```
feat/backend-<scope>     # backend changes only
feat/frontend-<scope>    # frontend changes only
feat/hermes-<scope>      # hermes-gateway changes only
fix/<domain>-<scope>     # bug fixes
```

## Parallel Sessions
- Setiap domain (backend/frontend/hermes) dikerjakan di git worktree terpisah
- Satu session = satu worktree = satu branch
- Jangan ada dua concurrent session yang nyentuh branch yang sama

## Commit Rules
- 1 commit = 1 domain (backend ATAU frontend, jangan campur)
- Format: `<domain>(<scope>): <deskripsi dalam Bahasa Indonesia>`
- Contoh yg benar:
  - `feat(frontend): consolidasi formatRupiah ke utils/formatter`
  - `fix(backend): perbaikan N+1 query di finance endpoint`
- Contoh yg salah:
  - `update stuff`
  - `backend changes + some frontend fixes`

## Workflow per Sesi
1. Bikin branch baru dari `main` (kalau belum ada worktree)
2. Kerjain task
3. `npm run build` atau `python -m pytest` — harus pass
4. Commit setiap task selesai
5. JANGAN ninggalin uncommitted changes di akhir sesi
6. Merge ke `main` hanya setelah semua test pass

## Domain Ownership
- `backend/` — FastAPI, SQLAlchemy, SQLite/MySQL
- `frontend/` — Next.js 14 App Router, TypeScript, Tailwind
- `hermes-gateway/` — aplikasi terpisah, hanya numpang di repo ini. Deploy & lifecycle berbeda dari kantorteman. Jangan campur commit hermes dengan backend/frontend.
