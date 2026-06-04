# Deployment
- Always push frontend changes to git remote (origin/main) for Vercel auto-deploy after fixes are complete. Confidence: 0.90
- NEVER use killall on shared hosting server — triggers LiteSpeed Passenger restart loop that exhausts all processes. Always use cPanel Python App panel to Stop/Start. Confidence: 0.90
- Build frontend inside the frontend/ folder directly; zip contents without a nested frontend/ prefix. User uploads build manually to hosting. Confidence: 0.85
- Backend restart must be done via cPanel > Setup Python App > Restart, not terminal commands. Confidence: 0.80
- Commit and push to git remote as milestones after completing significant changes, before continuing to next task. Confidence: 0.85
- On shared hosting with Passenger WSGI, .env file changes are NOT automatically picked up — use cPanel environment variables or set env vars directly in passenger_wsgi.py, and always Stop/Start the app after changes. Confidence: 0.80
- When developing frontend locally against production API, include `http://localhost:3000` in CORS_ORIGIN to avoid CORS blocks. Confidence: 0.70
