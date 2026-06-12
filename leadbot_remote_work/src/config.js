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
  waha: {
    baseUrl: process.env.WAHA_BASE_URL || 'http://127.0.0.1:3001',
    apiKey: process.env.WAHA_API_KEY || '',
    session: process.env.WAHA_SESSION || 'default',
    webhookSecret: process.env.WAHA_WEBHOOK_SECRET || process.env.WEBHOOK_SECRET || '',
    mediaDownload: boolFromEnv('WAHA_MEDIA_DOWNLOAD', false),
    maxMediaBytes: intFromEnv('WAHA_MAX_MEDIA_BYTES', 5 * 1024 * 1024),
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
  },
  ai: {
    provider: '9router',
    endpointStyle: 'openai',
    baseUrl: routerBaseFromEnv(),
    externalBaseUrl: process.env.NINE_ROUTER_EXTERNAL_URL || 'http://9router.kantorteman.my.id/v1',
    apiKey: process.env.AI_API_KEY || process.env.NINE_ROUTER_API_KEY || process.env.ROUTER_API_KEY || '',
    model: process.env.AI_MODEL || process.env.NINE_ROUTER_MODEL || 'combo-genflow',
    maxTokens: intFromEnv('AI_MAX_TOKENS', 450),
    timeoutMs: intFromEnv('AI_TIMEOUT_MS', 30000),
    confidenceThreshold: floatFromEnv('AI_CONFIDENCE_THRESHOLD', 0.7),
    temperature: floatFromEnv('AI_TEMPERATURE', 0.45),
  },
  security: {
    dashboardUser: process.env.DASHBOARD_USER || '',
    dashboardPassword: process.env.DASHBOARD_PASSWORD || '',
  },
  kantorteman: {
    apiUrl: process.env.KANTORTEMAN_API_URL || 'https://api.kantorteman.my.id',
    apiKey: process.env.KANTORTEMAN_API_KEY || '',
    bridgeToken: process.env.KANTORTEMAN_BRIDGE_TOKEN || process.env.KANTORTEMAN_API_KEY || '',
    bridgeDemo: boolFromEnv('KANTORTEMAN_BRIDGE_DEMO', true),
  },
};
