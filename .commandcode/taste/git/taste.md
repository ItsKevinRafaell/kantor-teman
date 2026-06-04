# git
- Use monorepo structure — backend, frontend, and hermes-gateway stay in one repo with domain-based branching instead of separate repos. Confidence: 0.75
- Use conventional commit format: feat(domain): <description> or fix(domain): <description>. Confidence: 0.75
- Use git worktree for parallel sessions — one worktree per domain branch to avoid conflicts. Confidence: 0.70
- Commit atomically per domain — never mix backend and frontend changes in one commit. Confidence: 0.75
- Never leave uncommitted changes at end of session — commit or stash before switching tasks. Confidence: 0.70
- Never work directly on main branch — all work via feature branches merged after verification. Confidence: 0.70
