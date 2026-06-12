const crypto = require('crypto');
const config = require('../config');

const SESSION_COOKIE = 'leadbot_session';
const SESSION_MAX_AGE_SECONDS = 60 * 60 * 12;

function isDashboardAuthEnabled() {
  return Boolean(config.security.dashboardUser && config.security.dashboardPassword);
}

function getSessionSecret() {
  return process.env.DASHBOARD_SESSION_SECRET || config.security.dashboardPassword || 'leadbot-dashboard';
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

function verifySession(req) {
  const value = parseCookies(req)[SESSION_COOKIE];
  if (!value) return false;

  const parts = value.split('.');
  if (parts.length !== 3) return false;

  const [user, expiresAtRaw, signature] = parts;
  const expiresAt = Number(expiresAtRaw);
  if (!user || !Number.isFinite(expiresAt) || expiresAt <= Date.now()) return false;
  if (!safeEqual(user, config.security.dashboardUser)) return false;

  return safeEqual(signature, signSession(user, expiresAt));
}

function verifyCredentials(user, password) {
  return safeEqual(user, config.security.dashboardUser) && safeEqual(password, config.security.dashboardPassword);
}

function verifyBasicAuth(req) {
  const header = req.get('authorization') || '';
  if (!header.startsWith('Basic ')) return false;

  let decoded = '';
  try {
    decoded = Buffer.from(header.slice(6), 'base64').toString('utf8');
  } catch (error) {
    return false;
  }

  const sep = decoded.indexOf(':');
  const user = sep >= 0 ? decoded.slice(0, sep) : '';
  const password = sep >= 0 ? decoded.slice(sep + 1) : '';
  return verifyCredentials(user, password);
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

function requireDashboardAuth(req, res, next) {
  if (!isDashboardAuthEnabled()) return next();

  if (verifySession(req)) return next();
  if (allowsBasicAuth(req) && verifyBasicAuth(req)) return next();

  return unauthorized(req, res);
}

function sanitizeNext(nextPath) {
  if (!nextPath || typeof nextPath !== 'string') return '/';
  if (!nextPath.startsWith('/') || nextPath.startsWith('//')) return '/';
  if (nextPath.startsWith('/login')) return '/';
  return nextPath;
}

function setSessionCookie(res, user) {
  const secure = process.env.DASHBOARD_COOKIE_SECURE === 'true' ? '; Secure' : '';
  res.setHeader(
    'Set-Cookie',
    SESSION_COOKIE + '=' + encodeURIComponent(createSessionValue(user)) + '; HttpOnly; SameSite=Lax; Path=/; Max-Age=' + SESSION_MAX_AGE_SECONDS + secure
  );
}

function clearSessionCookie(res) {
  res.setHeader('Set-Cookie', SESSION_COOKIE + '=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0');
}

function redirectIfAuthenticated(req, res, next) {
  if (!isDashboardAuthEnabled()) return res.redirect('/');
  if (verifySession(req)) return res.redirect('/');
  return next();
}

function handleLogin(req, res) {
  if (!isDashboardAuthEnabled()) return res.redirect('/');

  const user = req.body?.username || '';
  const password = req.body?.password || '';
  const nextPath = sanitizeNext(req.body?.next || req.query?.next);

  if (!verifyCredentials(user, password)) {
    return res.redirect('/login?error=1&next=' + encodeURIComponent(nextPath));
  }

  setSessionCookie(res, user);
  return res.redirect(nextPath);
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
