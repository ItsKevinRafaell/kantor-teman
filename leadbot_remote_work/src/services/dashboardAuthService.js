const crypto = require('crypto');
const net = require('net');
const tls = require('tls');
const db = require('../db');
const config = require('../config');

const RESET_TOKEN_TTL_MINUTES = 60;
const GENERIC_RESET_MESSAGE = 'Jika email terdaftar dan SMTP aktif, instruksi reset password akan dikirim.';

function normalizeEmail(email) {
  return String(email || '').trim().toLowerCase();
}

function isEmail(value) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);
}

function emailDomain(email) {
  return email.split('@').pop();
}

function isAllowedEmail(email) {
  const allowed = config.security.allowedEmailDomains || [];
  return allowed.length === 0 || allowed.includes(emailDomain(email));
}

function validateEmail(email) {
  const normalized = normalizeEmail(email);
  if (!isEmail(normalized)) throw new Error('Format email tidak valid');
  if (!isAllowedEmail(normalized)) throw new Error('Gunakan email resmi yang sudah ditentukan.');
  return normalized;
}

function validatePassword(password) {
  const value = String(password || '');
  if (value.length < 8) throw new Error('Password minimal 8 karakter.');
  if (value.length > 128) throw new Error('Password terlalu panjang.');
  return value;
}

function safeEqual(left, right) {
  const leftBuffer = Buffer.from(String(left || ''));
  const rightBuffer = Buffer.from(String(right || ''));
  if (leftBuffer.length !== rightBuffer.length) return false;
  return crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('base64url');
  const hash = crypto.scryptSync(validatePassword(password), salt, 64).toString('base64url');
  return ['scrypt', salt, hash].join('$');
}

function verifyPassword(password, storedHash) {
  const parts = String(storedHash || '').split('$');
  if (parts.length !== 3 || parts[0] !== 'scrypt') return false;
  const [, salt, expected] = parts;
  const actual = crypto.scryptSync(String(password || ''), salt, 64).toString('base64url');
  return safeEqual(actual, expected);
}

function hashResetToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

function encodeHeader(value) {
  return String(value || '').replace(/[\r\n]/g, ' ').trim();
}

function encodeBase64(value) {
  return Buffer.from(String(value || ''), 'utf8').toString('base64');
}

function readLine(socket, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    let buffer = '';
    const timeout = setTimeout(() => cleanup(() => reject(new Error('SMTP timeout'))), timeoutMs);

    function cleanup(done) {
      clearTimeout(timeout);
      socket.off('data', onData);
      socket.off('error', onError);
      done();
    }

    function onError(error) {
      cleanup(() => reject(error));
    }

    function onData(chunk) {
      buffer += chunk.toString('utf8');
      const lines = buffer.split(/\r?\n/).filter(Boolean);
      if (lines.length === 0) return;
      const last = lines[lines.length - 1];
      if (/^\d{3} /.test(last)) cleanup(() => resolve(lines.join('\n')));
    }

    socket.on('data', onData);
    socket.on('error', onError);
  });
}

async function smtpCommand(socket, command, expectedCodes) {
  if (command) socket.write(command + '\r\n');
  const response = await readLine(socket);
  const code = Number(String(response).slice(0, 3));
  if (!expectedCodes.includes(code)) {
    throw new Error('SMTP command failed: ' + code);
  }
  return response;
}

function openSmtpSocket(smtp) {
  return new Promise((resolve, reject) => {
    const options = { host: smtp.host, port: smtp.port, servername: smtp.host };
    const socket = smtp.port === 465 ? tls.connect(options) : net.connect(options);
    socket.setTimeout(30000);
    if (smtp.port === 465) {
      socket.once('secureConnect', () => resolve(socket));
    } else {
      socket.once('connect', () => resolve(socket));
    }
    socket.once('timeout', () => {
      socket.destroy();
      reject(new Error('SMTP connection timeout'));
    });
    socket.once('error', reject);
  });
}

async function upgradeStartTls(socket, smtp) {
  await smtpCommand(socket, 'STARTTLS', [220]);
  return new Promise((resolve, reject) => {
    const secureSocket = tls.connect({
      socket,
      servername: smtp.host,
    });
    secureSocket.once('secureConnect', () => resolve(secureSocket));
    secureSocket.once('error', reject);
  });
}

async function getUserById(id) {
  const result = await db.query(
    'SELECT id, email, name, role, active FROM dashboard_users WHERE id = $1',
    [id]
  );
  return result.rows[0] || null;
}

async function getUserByEmail(email) {
  const result = await db.query(
    'SELECT id, email, name, role, active, password_hash FROM dashboard_users WHERE LOWER(email) = LOWER($1)',
    [email]
  );
  return result.rows[0] || null;
}

async function authenticate(email, password) {
  const normalized = validateEmail(email);
  const user = await getUserByEmail(normalized);
  if (!user || !user.active || !verifyPassword(password, user.password_hash)) return null;
  return user;
}

function bootstrapEmailFromEnv() {
  const explicit = normalizeEmail(config.security.dashboardEmail);
  if (explicit) return explicit;
  const legacyUser = normalizeEmail(config.security.dashboardUser);
  if (legacyUser.includes('@')) return legacyUser;
  return 'admin@temanumkmkita.com';
}

async function ensureBootstrapUser() {
  if (config.security.dashboardAuthDisabled) return;
  const countResult = await db.query('SELECT COUNT(*)::int AS count FROM dashboard_users');
  if (countResult.rows[0]?.count > 0) return;

  const password = config.security.dashboardPassword;
  if (!password) {
    console.warn('[Auth] No dashboard user exists and DASHBOARD_PASSWORD is empty. Dashboard login is locked.');
    return;
  }

  const email = validateEmail(bootstrapEmailFromEnv());
  await db.query(
    `INSERT INTO dashboard_users (email, name, password_hash, role, active)
     VALUES ($1, $2, $3, 'admin', true)
     ON CONFLICT (email) DO NOTHING`,
    [email, config.security.dashboardName, hashPassword(password)]
  );
  console.log('[Auth] Bootstrap dashboard user ensured.');
}

async function sendPasswordResetEmail(toEmail, resetUrl) {
  const smtp = config.smtp;
  if (!smtp.host || !smtp.user || !smtp.password) return false;

  const from = smtp.from || smtp.user;
  const body = [
    'Halo,',
    '',
    'Ada permintaan reset password untuk akun AutoLead.',
    'Buka link berikut untuk membuat password baru:',
    resetUrl,
    '',
    `Link berlaku ${RESET_TOKEN_TTL_MINUTES} menit. Abaikan email ini kalau kamu tidak meminta reset password.`,
  ].join('\n');
  const message = [
    `From: ${encodeHeader(from)}`,
    `To: ${encodeHeader(toEmail)}`,
    'Subject: Reset password AutoLead',
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
    '',
    body,
  ].join('\r\n');

  let socket = await openSmtpSocket(smtp);
  try {
    await smtpCommand(socket, null, [220]);
    await smtpCommand(socket, 'EHLO autolead.local', [250]);
    if (smtp.port !== 465) {
      socket = await upgradeStartTls(socket, smtp);
      await smtpCommand(socket, 'EHLO autolead.local', [250]);
    }
    await smtpCommand(socket, 'AUTH LOGIN', [334]);
    await smtpCommand(socket, encodeBase64(smtp.user), [334]);
    await smtpCommand(socket, encodeBase64(smtp.password), [235]);
    await smtpCommand(socket, `MAIL FROM:<${from}>`, [250]);
    await smtpCommand(socket, `RCPT TO:<${toEmail}>`, [250, 251]);
    await smtpCommand(socket, 'DATA', [354]);
    socket.write(message.replace(/\n\./g, '\n..') + '\r\n.\r\n');
    await smtpCommand(socket, null, [250]);
    await smtpCommand(socket, 'QUIT', [221]);
  } finally {
    socket.destroy();
  }

  return true;
}

async function requestPasswordReset(email, baseUrl) {
  const normalized = normalizeEmail(email);
  if (!isEmail(normalized) || !isAllowedEmail(normalized)) {
    return { ok: true, message: GENERIC_RESET_MESSAGE };
  }

  const user = await getUserByEmail(normalized);
  if (!user || !user.active) return { ok: true, message: GENERIC_RESET_MESSAGE };

  const rawToken = crypto.randomBytes(32).toString('base64url');
  await db.query(
    `INSERT INTO dashboard_password_reset_tokens (user_id, token_hash, expires_at)
     VALUES ($1, $2, NOW() + ($3 * interval '1 minute'))`,
    [user.id, hashResetToken(rawToken), RESET_TOKEN_TTL_MINUTES]
  );

  const publicUrl = String(baseUrl || config.app.publicUrl).replace(/\/+$/, '');
  const resetUrl = publicUrl + '/reset-password?token=' + encodeURIComponent(rawToken);
  try {
    const sent = await sendPasswordResetEmail(user.email, resetUrl);
    if (!sent) console.warn('[PASSWORD_RESET] SMTP not configured; reset email not sent.');
  } catch (error) {
    console.warn('[PASSWORD_RESET] email failed:', error.name || 'Error');
  }

  return { ok: true, message: GENERIC_RESET_MESSAGE };
}

async function resetPassword(token, password) {
  const rawToken = String(token || '').trim();
  validatePassword(password);
  if (rawToken.length < 32 || rawToken.length > 256) {
    throw new Error('Token reset tidak valid atau sudah dipakai.');
  }

  const result = await db.query(
    `SELECT id, user_id
     FROM dashboard_password_reset_tokens
     WHERE token_hash = $1
       AND used_at IS NULL
       AND expires_at > NOW()
     LIMIT 1`,
    [hashResetToken(rawToken)]
  );
  const row = result.rows[0];
  if (!row) throw new Error('Token reset tidak valid atau sudah dipakai.');

  const client = await db.connect();
  try {
    await client.query('BEGIN');
    await client.query(
      'UPDATE dashboard_users SET password_hash = $1, updated_at = NOW() WHERE id = $2',
      [hashPassword(password), row.user_id]
    );
    await client.query(
      'UPDATE dashboard_password_reset_tokens SET used_at = NOW() WHERE id = $1',
      [row.id]
    );
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }

  return { ok: true };
}

module.exports = {
  authenticate,
  ensureBootstrapUser,
  getUserById,
  requestPasswordReset,
  resetPassword,
};
