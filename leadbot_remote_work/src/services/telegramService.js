const config = require('../config');

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

class TelegramService {
  constructor() {
    this.botToken = config.telegram.botToken;
    this.adminId = config.admin.telegramId;
  }

  async sendMessage(text) {
    if (!this.botToken || !this.adminId) {
      console.log('[Telegram] Bot not configured');
      return { success: false, error: 'Not configured' };
    }

    try {
      const response = await fetch('https://api.telegram.org/bot' + this.botToken + '/sendMessage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: this.adminId, text, parse_mode: 'HTML' }),
      });
      const data = await response.json();
      if (!data.ok) return { success: false, error: data.description };
      return { success: true };
    } catch (error) {
      console.error('[Telegram] Error:', error.message);
      return { success: false, error: error.message };
    }
  }

  async notifyNewConversation(phone, name, message) {
    const text = '<b>Percakapan Baru</b>\n\n' +
      'Nomor: ' + escapeHtml(phone) + '\n' +
      'Nama: ' + escapeHtml(name || 'Unknown') + '\n' +
      'Pesan: ' + escapeHtml(message);
    return this.sendMessage(text);
  }

  async notifyEscalation(phone, name, reason) {
    const text = '<b>Eskalasi</b>\n\n' +
      'Nomor: ' + escapeHtml(phone) + '\n' +
      'Nama: ' + escapeHtml(name || 'Unknown') + '\n' +
      'Alasan: ' + escapeHtml(reason) + '\n\n' +
      'Ambil alih dari dashboard.';
    return this.sendMessage(text);
  }

  async notifyStats(summary) {
    const text = '<b>Ringkasan Harian</b>\n\n' +
      'Total: ' + summary.total + '\n' +
      'Aktif: ' + summary.active + '\n' +
      'Eskalasi: ' + summary.escalated + '\n' +
      'Pesan Hari Ini: ' + summary.messagesToday;
    return this.sendMessage(text);
  }
}

module.exports = new TelegramService();
