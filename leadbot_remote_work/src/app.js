const express = require('express');
const path = require('path');
const config = require('./config');
const webhookRoutes = require('./routes/webhook');
const dashboardRoutes = require('./routes/dashboard');
const db = require('./db');
const runMigrations = require('./migrate');
const telegramPolling = require('./services/telegramPolling');
const {
  requireDashboardAuth,
  isDashboardAuthEnabled,
  redirectIfAuthenticated,
  handleLogin,
  handleLogout,
} = require('./middleware/auth');

const app = express();
const publicDir = path.join(__dirname, '../public');

app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));

app.use((req, res, next) => {
  console.log('[' + new Date().toISOString() + '] ' + req.method + ' ' + req.path);
  next();
});

app.use('/api', webhookRoutes);
app.get('/login', redirectIfAuthenticated, (req, res) => {
  res.sendFile(path.join(publicDir, 'login.html'));
});
app.post('/login', handleLogin);
app.post('/logout', handleLogout);
app.use('/api/dashboard', requireDashboardAuth, dashboardRoutes);
app.use(requireDashboardAuth, express.static(publicDir, { index: false }));

app.get('/', requireDashboardAuth, (req, res) => {
  res.sendFile(path.join(publicDir, 'index.html'));
});

app.get('/api', (req, res) => {
  res.json({
    name: 'LeadBot API',
    version: '1.1.0',
    status: 'running',
    dashboardAuth: isDashboardAuthEnabled() ? 'enabled' : 'disabled',
    endpoints: {
      health: 'GET /api/health',
      webhook: 'POST /api/webhook',
      dashboard: 'GET /api/dashboard/*',
    },
  });
});

app.post('/api/telegram-webhook', express.json(), async (req, res) => {
  try {
    if (req.body?.message) await telegramPolling.handleUpdate(req.body);
    res.json({ ok: true });
  } catch (error) {
    console.error('[Telegram Webhook] Error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.use((err, req, res, next) => {
  console.error('[Error]', err);
  res.status(500).json({ error: 'Internal server error' });
});

async function testConnection() {
  await db.query('SELECT 1');
  console.log('[DB] Connected to PostgreSQL');
}

async function start() {
  try {
    await testConnection();
    await runMigrations();
  } catch (error) {
    console.error('[Bootstrap] Failed:', error.message);
    process.exit(1);
  }

  const port = config.app.port;
  app.listen(port, '0.0.0.0', () => {
    console.log('[App] LeadBot running on port ' + port);
    console.log('[App] Dashboard auth: ' + (isDashboardAuthEnabled() ? 'enabled' : 'disabled'));
  });

  telegramPolling.start().catch((err) => console.log('[Telegram] Polling not started:', err.message));
}

start();
