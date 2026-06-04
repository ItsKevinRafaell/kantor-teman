# UI/UX
- Use custom modal components for all confirmations (create, delete, update) — never use JavaScript built-in `confirm()` or `alert()`. Confidence: 0.75
- Use Lucide icons instead of emoji in pipeline docs and UI elements. Confidence: 0.85
- Never use purple/indigo colors (`bg-purple-*`, `text-purple-*`, `bg-indigo-*`) anywhere in the UI. Replace all with amber/yellow (`bg-amber-500`, `text-amber-600`). User requested full purge 3+ times. Confidence: 0.85
- Yellow/amber buttons must have white text, not dark text. Confidence: 0.70
- Login page must be a clean standalone page — no sidebar, no topbar, no navigation elements. Confidence: 0.80
- All dashboard pages (proposals, clients, dashboard, etc.) must use realtime polling for data updates — no manual refresh required. Confidence: 0.65
