const config = require('../config');

function joinUrl(base, path) {
  return String(base || '').replace(/\/+$/, '') + '/' + String(path || '').replace(/^\/+/, '');
}

function normalizePhone(value) {
  let phone = String(value || '').trim();
  if (!phone) return '';
  phone = phone
    .replace(/@c\.us$/i, '')
    .replace(/@s\.whatsapp\.net$/i, '')
    .replace(/@g\.us$/i, '')
    .replace(/[^\d+]/g, '');
  if (phone.startsWith('+')) phone = phone.slice(1);
  if (phone.startsWith('00')) phone = phone.slice(2);
  if (phone.startsWith('0')) phone = '62' + phone.slice(1);
  if (phone.startsWith('8')) phone = '62' + phone;
  return phone;
}

function pickPayload(body) {
  if (Array.isArray(body)) return body[0] || {};
  return body?.payload || body?.data || body?.message_data || body || {};
}

function pickMessageText(payload) {
  return payload.message
    || payload.text
    || payload.body
    || payload.caption
    || payload.button
    || payload.pollname
    || '';
}

class FonnteService {
  constructor() {
    this.baseUrl = config.fonnte.baseUrl;
    this.token = config.fonnte.token;
    this.countryCode = config.fonnte.countryCode;
    this.connectOnly = config.fonnte.connectOnly;
    this.timeoutMs = config.fonnte.timeoutMs;
  }

  getStatus() {
    return {
      provider: 'fonnte',
      configured: Boolean(this.token),
      baseUrl: this.baseUrl,
      tokenConfigured: Boolean(this.token),
      countryCode: this.countryCode,
      connectOnly: this.connectOnly,
    };
  }

  normalizePhone(value) {
    return normalizePhone(value);
  }

  async sendMessage(target, message, options = {}) {
    if (!this.token) return { success: false, error: 'FONNTE_TOKEN belum dikonfigurasi' };

    const phone = normalizePhone(target);
    const text = String(message || '').trim();
    if (!phone) return { success: false, error: 'Nomor WhatsApp tidak valid' };
    if (!text) return { success: false, error: 'Pesan kosong' };

    const payload = {
      target: phone,
      message: text,
      countryCode: String(options.countryCode || this.countryCode || '62'),
      connectOnly: options.connectOnly ?? this.connectOnly,
    };
    if (options.delay !== undefined) payload.delay = String(options.delay);
    if (options.typing !== undefined) payload.typing = options.typing;
    if (options.inboxId || options.inboxid) payload.inboxid = String(options.inboxId || options.inboxid);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs || this.timeoutMs);

    try {
      const response = await fetch(joinUrl(this.baseUrl, '/send'), {
        method: 'POST',
        headers: {
          Authorization: this.token,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      const textBody = await response.text();
      let data = textBody;
      try { data = textBody ? JSON.parse(textBody) : {}; } catch (error) {}

      const providerError = typeof data === 'object'
        ? data.reason || data.message || data.error || data.detail
        : data;
      const providerRejected = data?.status === false || data?.Status === false;
      if (!response.ok || providerRejected) {
        return {
          success: false,
          status: response.status,
          error: providerError || 'Fonnte request failed',
          data,
        };
      }

      return { success: true, status: response.status, data };
    } catch (error) {
      const messageText = error.name === 'AbortError' ? 'Fonnte request timeout' : error.message;
      return { success: false, error: messageText };
    } finally {
      clearTimeout(timeout);
    }
  }

  parseWebhookPayload(body) {
    const payload = pickPayload(body);
    const rawSender = payload.sender || payload.from || payload.target || payload.phone || payload.number || body?.sender || '';
    const sender = normalizePhone(rawSender);
    const message = String(pickMessageText(payload) || '').trim();
    const name = payload.name || payload.pushName || payload.contact_name || payload.member || null;
    const externalId = payload.inboxid || payload.inbox_id || payload.id || payload.messageId || null;
    const location = payload.location || null;
    const hasMedia = Boolean(payload.url || payload.file || payload.media || payload.filename || payload.mimetype);

    return {
      sender,
      message,
      name,
      fromMe: payload.fromMe === true || payload.from_me === true,
      externalId: externalId ? String(externalId) : null,
      messageType: hasMedia ? 'media' : 'text',
      media: hasMedia ? {
        url: payload.url || payload.media?.url || null,
        filename: payload.filename || payload.media?.filename || null,
        mimetype: payload.mimetype || payload.media?.mimetype || null,
        caption: payload.caption || null,
      } : null,
      location,
      rawEvent: body?.event || body?.type || payload.type || payload.status || 'message',
      rawPayload: payload,
    };
  }
}

module.exports = new FonnteService();
