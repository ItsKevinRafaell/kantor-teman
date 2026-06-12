const config = require('../config');

function joinUrl(base, path) {
  return String(base || '').replace(/\/+$/, '') + '/' + String(path || '').replace(/^\/+/, '');
}

function normalizePhone(value) {
  let phone = String(value || '').trim();
  if (!phone) return '';
  phone = phone.replace(/@c\.us$/i, '').replace(/@s\.whatsapp\.net$/i, '').replace(/[^\d+]/g, '');
  if (phone.startsWith('+')) phone = phone.slice(1);
  if (phone.startsWith('0')) phone = '62' + phone.slice(1);
  if (phone.startsWith('8')) phone = '62' + phone;
  return phone;
}

function toChatId(value) {
  const phone = normalizePhone(value);
  return phone.includes('@') ? phone : phone + '@c.us';
}

function pickPayload(body) {
  return body?.payload || body?.data || body?.message || body || {};
}

function pickMessageText(payload) {
  return payload.body
    || payload.text
    || payload.caption
    || payload.message?.conversation
    || payload.message?.extendedTextMessage?.text
    || payload._data?.body
    || payload._data?.caption
    || '';
}

class WahaService {
  constructor() {
    this.baseUrl = config.waha.baseUrl;
    this.apiKey = config.waha.apiKey;
    this.session = config.waha.session;
  }

  headers(extra = {}) {
    const headers = { ...extra };
    if (this.apiKey) headers['X-Api-Key'] = this.apiKey;
    return headers;
  }

  async request(path, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs || 15000);
    try {
      const response = await fetch(joinUrl(this.baseUrl, path), {
        ...options,
        headers: this.headers(options.headers || {}),
        signal: controller.signal,
      });
      const text = await response.text();
      let data = text;
      try { data = text ? JSON.parse(text) : {}; } catch (error) {}
      if (!response.ok) {
        const message = typeof data === 'object' ? (data.message || data.error || JSON.stringify(data)) : data;
        return { success: false, status: response.status, error: message || 'WAHA request failed' };
      }
      return { success: true, status: response.status, data };
    } catch (error) {
      const message = error.name === 'AbortError' ? 'WAHA request timeout' : error.message;
      return { success: false, error: message };
    } finally {
      clearTimeout(timeout);
    }
  }

  getStatus() {
    return {
      configured: Boolean(this.baseUrl),
      baseUrl: this.baseUrl,
      session: this.session,
      apiKeyConfigured: Boolean(this.apiKey),
    };
  }

  normalizePhone(value) {
    return normalizePhone(value);
  }

  toChatId(value) {
    return toChatId(value);
  }

  async getSessionStatus() {
    const byName = await this.request('/api/sessions/' + encodeURIComponent(this.session));
    if (byName.success) return byName;
    return this.request('/api/sessions');
  }

  async startSession() {
    const create = await this.request('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: this.session, start: true }),
    });
    if (create.success || create.status === 409) return this.request('/api/sessions/' + encodeURIComponent(this.session) + '/start', { method: 'POST' });
    return create;
  }

  async stopSession() {
    return this.request('/api/sessions/' + encodeURIComponent(this.session) + '/stop', { method: 'POST' });
  }

  async getQr() {
    return this.request('/api/' + encodeURIComponent(this.session) + '/auth/qr', {
      headers: { Accept: 'application/json,text/plain,image/png,*/*' },
    });
  }

  async requestPairingCode(phoneNumber) {
    return this.request('/api/' + encodeURIComponent(this.session) + '/auth/request-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phoneNumber: normalizePhone(phoneNumber) }),
    });
  }

  async sendMessage(target, message) {
    if (!this.baseUrl) return { success: false, error: 'WAHA_BASE_URL belum dikonfigurasi' };
    const text = String(message || '').trim();
    if (!text) return { success: false, error: 'Pesan kosong' };
    const result = await this.request('/api/sendText', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session: this.session,
        chatId: toChatId(target),
        text,
      }),
    });
    if (!result.success) console.error('[WAHA] Send failed:', result.error);
    return result;
  }

  parseWebhookPayload(body) {
    const payload = pickPayload(body);
    const rawFrom = payload.from || payload.chatId || payload.remoteJid || payload.id?.remote || body?.from;
    const fromMe = payload.fromMe === true || payload.id?.fromMe === true || payload._data?.id?.fromMe === true;
    const sender = normalizePhone(rawFrom);
    const message = String(pickMessageText(payload) || '').trim();
    const name = payload.notifyName || payload.pushName || payload.sender?.pushName || payload._data?.notifyName || body?.name || null;
    const externalId = payload.id?.id || payload.id || payload.messageId || payload._data?.id?._serialized || null;
    const hasMedia = Boolean(payload.hasMedia || payload.media || payload.mimetype || payload._data?.hasMedia);

    return {
      sender,
      message,
      name,
      fromMe,
      externalId: typeof externalId === 'string' ? externalId : null,
      messageType: hasMedia ? 'media' : 'text',
      media: hasMedia ? {
        mimetype: payload.mimetype || payload.media?.mimetype || payload._data?.mimetype || null,
        filename: payload.filename || payload.media?.filename || null,
        caption: payload.caption || null,
      } : null,
      rawEvent: body?.event || body?.type || payload.type || 'message',
    };
  }
}

module.exports = new WahaService();
