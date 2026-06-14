const crypto = require('crypto');
const config = require('../config');
const dashboardAuthService = require('../services/dashboardAuthService');

const SESSION_COOKIE = 'leadbot_session';
const SESSION_MAX_AGE_SECONDS = 60 * 60 * 12;

function isDashboardAuthEnabled() {
  return !config.security.dashboardAuthDisabled;
}

function getSessionSecret() {
  return config.security.dashboardSessionSecret || config.security.dashboardPassword || 'leadbot-dashboard';
}

function safeEqual(left, right) {
  const leftBuffer = Buffer.from(String(left || ''));
  const rightBuffer = Buffer.from(String(right || ''));
  if (leftBuffer.length !== rightBuffer.length) return false;
  return crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function parseCookies(req) {
  return String(req.headers.cookie || '')
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean)
    .reduce((cookies, part) => {
      const sep = part.indexOf('=');
      if (sep < 0) return cookies;
      cookies[decodeURIComponent(part.slice(0, sep))] = decodeURIComponent(part.slice(sep + 1));
      return cookies;
    }, {});
}

function signSession(user, expiresAt) {
  return crypto
    .createHmac('sha256', getSessionSecret())
    .update(user + '.' + expiresAt)
    .digest('base64url');
}

function createSessionValue(user) {
  const expiresAt = Date.now() + SESSION_MAX_AGE_SECONDS * 1000;
  return [user, expiresAt, signSession(user, expiresAt)].join('.');
}

async function verifySession(req) {
  const value = parseCookies(req)[SESSION_COOKIE];
  if (!value) return false;

  const parts = value.split('.');
  if (parts.length !== 3) return false;

  const [user, expiresAtRaw, signature] = parts;
  const expiresAt = Number(expiresAtRaw);
  if (!user || !Number.isFinite(expiresAt) || expiresAt <= Date.now()) return false;
  const dashboardUser = await dashboardAuthService.getUserById(user);
  if (!dashboardUser || !dashboardUser.active) return false;

  return safeEqual(signature, signSession(user, expiresAt));
}

async function verifyBasicAuth(req) {
  const header = req.get('authorization') || '';
  if (!header.startsWith('Basic ')) return false;

  let decoded = '';
  try {
    decoded = Buffer.from(header.slice(6), 'base64').toString('utf8');
  } catch (error) {
    return false;
  }

  const sep = decoded.indexOf(':');
  const email = sep >= 0 ? decoded.slice(0, sep) : '';
  const password = sep >= 0 ? decoded.slice(sep + 1) : '';
  return Boolean(await dashboardAuthService.authenticate(email, password));
}

function wantsHtml(req) {
  return req.method === 'GET' && !req.originalUrl.startsWith('/api/') && String(req.get('accept') || '').includes('text/html');
}

function allowsBasicAuth(req) {
  return req.originalUrl.startsWith('/api/dashboard/');
}

function unauthorized(req, res) {
  if (wantsHtml(req)) {
    const next = encodeURIComponent(req.originalUrl || '/');
    return res.redirect('/login?next=' + next);
  }

  return res.status(401).json({ error: 'Autentikasi dibutuhkan' });
}

async function requireDashboardAuth(req, res, next) {
  try {
    if (!isDashboardAuthEnabled()) return next();

    if (await verifySession(req)) return next();
    if (allowsBasicAuth(req) && await verifyBasicAuth(req)) return next();

    return unauthorized(req, res);
  } catch (error) {
    console.error('[Auth] Dashboard auth check failed:', error.message);
    return res.status(503).json({ error: 'Autentikasi sementara tidak tersedia' });
  }
}

function sanitizeNext(nextPath) {
  if (!nextPath || typeof nextPath !== 'string') return '/';
  if (!nextPath.startsWith('/') || nextPath.startsWith('//')) return '/';
  if (nextPath.startsWith('/login')) return '/';
  return nextPath;
}

function setSessionCookie(res, userId) {
  const secure = process.env.DASHBOARD_COOKIE_SECURE === 'true' ? '; Secure' : '';
  res.setHeader(
    'Set-Cookie',
    SESSION_COOKIE + '=' + encodeURIComponent(createSessionValue(userId)) + '; HttpOnly; SameSite=Lax; Path=/; Max-Age=' + SESSION_MAX_AGE_SECONDS + secure
  );
}

function clearSessionCookie(res) {
  res.setHeader('Set-Cookie', SESSION_COOKIE + '=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0');
}

async function redirectIfAuthenticated(req, res, next) {
  try {
    if (!isDashboardAuthEnabled()) return res.redirect('/');
    if (await verifySession(req)) return res.redirect('/');
    return next();
  } catch (error) {
    console.error('[Auth] Session check failed:', error.message);
    return next();
  }
}

async function handleLogin(req, res) {
  try {
    if (!isDashboardAuthEnabled()) return res.redirect('/');

    const email = req.body?.email || req.body?.username || '';
    const password = req.body?.password || '';
    const nextPath = sanitizeNext(req.body?.next || req.query?.next);
    const user = await dashboardAuthService.authenticate(email, password).catch(() => null);

    if (!user) {
      return res.redirect('/login?error=1&next=' + encodeURIComponent(nextPath));
    }

    setSessionCookie(res, user.id);
    return res.redirect(nextPath);
  } catch (error) {
    console.error('[Auth] Login failed:', error.message);
    return res.redirect('/login?error=1');
  }
}

function handleLogout(req, res) {
  clearSessionCookie(res);
  return res.redirect('/login?logged_out=1');
}

module.exports = {
  requireDashboardAuth,
  isDashboardAuthEnabled,
  redirectIfAuthenticated,
  handleLogin,
  handleLogout,
};
