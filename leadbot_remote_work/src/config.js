require('dotenv').config();

function intFromEnv(name, fallback) {
  const value = parseInt(process.env[name], 10);
  return Number.isFinite(value) ? value : fallback;
}

function floatFromEnv(name, fallback) {
  const value = parseFloat(process.env[name]);
  return Number.isFinite(value) ? value : fallback;
}

function boolFromEnv(name, fallback) {
  const value = process.env[name];
  if (value === undefined || value === '') return fallback;
  return ['1', 'true', 'yes', 'on'].includes(String(value).trim().toLowerCase());
}

function listFromEnv(name, fallback) {
  return String(process.env[name] || fallback || '')
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function routerBaseFromEnv() {
  const candidates = [
    process.env.NINE_ROUTER_URL,
    process.env.AI_BASE_URL,
    process.env.OPENAI_BASE_URL,
  ];
  const selected = candidates.find((value) => {
    const normalized = String(value || '').toLowerCase();
    return normalized.includes('9router') || normalized.includes('127.0.0.1:20128') || normalized.includes('localhost:20128');
  });
  return String(selected || 'http://127.0.0.1:20128/v1').replace(/\/+$/, '');
}

module.exports = {
  db: {
    host: process.env.DB_HOST || 'localhost',
    port: intFromEnv('DB_PORT', 5432),
    database: process.env.DB_NAME || 'leadbot_db',
    user: process.env.DB_USER || 'leadbot',
    password: process.env.DB_PASSWORD,
  },
  fonnte: {
    baseUrl: (process.env.FONNTE_BASE_URL || 'https://api.fonnte.com').replace(/\/+$/, ''),
    token: process.env.FONNTE_TOKEN || process.env.FONNTE_API_KEY || '',
    webhookSecret: process.env.FONNTE_WEBHOOK_SECRET || process.env.WEBHOOK_SECRET || '',
    countryCode: process.env.FONNTE_COUNTRY_CODE || '62',
    connectOnly: boolFromEnv('FONNTE_CONNECT_ONLY', true),
    timeoutMs: intFromEnv('FONNTE_TIMEOUT_MS', 20000),
  },
  telegram: {
    botToken: process.env.TELEGRAM_BOT_TOKEN,
  },
  admin: {
    telegramId: process.env.ADMIN_TELEGRAM_ID,
  },
  app: {
    port: intFromEnv('PORT', 3000),
    env: process.env.NODE_ENV || 'development',
    publicUrl: (process.env.AUTOLEAD_PUBLIC_URL || 'https://autolead.kantorteman.my.id').replace(/\/+$/, ''),
  },
  ai: {
    provider: '9router',
    endpointStyle: '9router-compatible',
    baseUrl: routerBaseFromEnv(),
    externalBaseUrl: process.env.NINE_ROUTER_EXTERNAL_URL || 'https://9router.kantorteman.my.id/v1',
    apiKey: process.env.AI_API_KEY || process.env.NINE_ROUTER_API_KEY || process.env.ROUTER_API_KEY || '',
    model: process.env.AI_MODEL || process.env.NINE_ROUTER_MODEL || 'combo-genflow',
    maxTokens: intFromEnv('AI_MAX_TOKENS', 450),
    timeoutMs: intFromEnv('AI_TIMEOUT_MS', 30000),
    confidenceThreshold: floatFromEnv('AI_CONFIDENCE_THRESHOLD', 0.7),
    temperature: floatFromEnv('AI_TEMPERATURE', 0.45),
  },
  security: {
    allowedEmailDomains: listFromEnv('AUTH_ALLOWED_EMAIL_DOMAINS', 'temanumkmkita.com'),
    dashboardEmail: process.env.DASHBOARD_EMAIL || '',
    dashboardName: process.env.DASHBOARD_NAME || 'AutoLead Admin',
    dashboardUser: process.env.DASHBOARD_USER || '',
    dashboardPassword: process.env.DASHBOARD_PASSWORD || '',
    dashboardAuthDisabled: boolFromEnv('DASHBOARD_AUTH_DISABLED', false),
    dashboardSessionSecret: process.env.DASHBOARD_SESSION_SECRET || '',
  },
  smtp: {
    host: process.env.SMTP_HOST || '',
    port: intFromEnv('SMTP_PORT', 587),
    user: process.env.SMTP_USER || '',
    password: process.env.SMTP_PASSWORD || '',
    from: process.env.SMTP_FROM || process.env.SMTP_USER || 'noreply@temanumkmkita.com',
  },
  kantorteman: {
    apiUrl: process.env.KANTORTEMAN_API_URL || 'https://api.kantorteman.my.id',
    apiKey: process.env.KANTORTEMAN_API_KEY || '',
    bridgeToken: process.env.KANTORTEMAN_BRIDGE_TOKEN || process.env.KANTORTEMAN_API_KEY || '',
    bridgeDemo: boolFromEnv('KANTORTEMAN_BRIDGE_DEMO', true),
  },
};
